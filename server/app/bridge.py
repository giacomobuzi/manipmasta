"""Ponte verso la macchina: cache stato, eventi, risposte, storico cicli, push WebSocket.

`MachineLink` contiene tutta la logica e non dipende dal trasporto: `MqttLink` lo collega
a paho-mqtt v2 (client in thread), i test usano una sottoclasse finta.
"""
from __future__ import annotations

import asyncio
import collections
import json
import logging
import threading
import time
from typing import Any

from . import protocol
from .config import Settings
from .db import Database

log = logging.getLogger("manipmasta.bridge")


class Hub:
    """Distribuisce messaggi `{"type","data"}` ai client WebSocket (thread-safe)."""

    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None
        self.queues: set[asyncio.Queue] = set()

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        self.queues.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.queues.discard(q)

    def _put(self, msg: dict) -> None:
        for q in list(self.queues):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:  # client lento: scarta il più vecchio
                try:
                    q.get_nowait()
                    q.put_nowait(msg)
                except Exception:
                    pass

    def publish(self, mtype: str, data: Any) -> None:
        msg = {"type": mtype, "data": data}
        if self.loop is None or self.loop.is_closed():
            return
        try:
            self.loop.call_soon_threadsafe(self._put, msg)
        except RuntimeError:
            pass


class MachineLink:
    """Stato macchina + logica comandi/eventi. I sottotipi implementano `_publish_cmd`."""

    def __init__(self, settings: Settings, db: Database, hub: Hub) -> None:
        self.settings = settings
        self.db = db
        self.hub = hub
        self.state: dict | None = None
        self.state_ts: float = 0.0
        self.online: bool = False
        self.connected: bool = False
        self.events: collections.deque = collections.deque(maxlen=300)
        self._lock = threading.Lock()
        self._waiters: list[tuple[str, asyncio.AbstractEventLoop, asyncio.Future]] = []
        self._pending_run: dict | None = None
        self._cmd_lock: asyncio.Lock | None = None

    # ------------------------------------------------------------ trasporto
    def start(self) -> None:  # pragma: no cover - sovrascritto
        pass

    def stop(self) -> None:  # pragma: no cover - sovrascritto
        pass

    def _publish_cmd(self, line: str) -> bool:
        raise NotImplementedError

    # ------------------------------------------------------------ comandi
    async def send(self, line: str, run_ctx: dict | None = None,
                   timeout: float | None = None) -> dict:
        """Pubblica un comando già validato e attende la risposta `resp` (max timeout)."""
        timeout = self.settings.resp_timeout if timeout is None else timeout
        kw = line.split()[0].upper()
        if kw == "RUN":
            if run_ctx is None:
                p = protocol.run_params(protocol.parse_run_args(line.split()[1:]))
                run_ctx = {"recipe_id": None, "recipe_name": None,
                           "np": _safe_np(p)}
            self._pending_run = {**run_ctx, "run_line": line, "ts": time.time()}

        if self._cmd_lock is None:
            self._cmd_lock = asyncio.Lock()
        # STOP non aspetta mai dietro ad altri comandi
        if kw == "STOP":
            return await self._send_wait(kw, line, timeout)
        async with self._cmd_lock:
            return await self._send_wait(kw, line, timeout)

    async def _send_wait(self, kw: str, line: str, timeout: float) -> dict:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        entry = (kw, loop, fut)
        with self._lock:
            self._waiters.append(entry)
        try:
            if not self._publish_cmd(line):
                return {"sent": False, "cmd": line, "resp": None, "ok": False, "timeout": False}
            self.hub.publish("cmd", line)
            try:
                resp = await asyncio.wait_for(fut, timeout)
            except asyncio.TimeoutError:
                resp = None
        finally:
            with self._lock:
                if entry in self._waiters:
                    self._waiters.remove(entry)
        ok = bool(resp and resp.upper().startswith("OK"))
        return {"sent": True, "cmd": line, "resp": resp, "ok": ok, "timeout": resp is None}

    # ------------------------------------------------------------ ingresso
    def handle_message(self, topic: str, payload: bytes | str) -> None:
        """Chiamato dal thread MQTT (o dai test) per ogni messaggio ricevuto."""
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", "replace")
        name = topic.rsplit("/", 1)[-1]
        try:
            if name == "state":
                self._on_state(payload)
            elif name == "event":
                self._on_event(payload.strip())
            elif name == "resp":
                self._on_resp(payload.strip())
            elif name == "online":
                self.online = payload.strip() == "1"
                self.hub.publish("online", self.online)
        except Exception:  # un messaggio malformato non deve fermare il client MQTT
            log.exception("errore gestendo %s", topic)

    def _on_state(self, payload: str) -> None:
        try:
            st = json.loads(payload)
        except json.JSONDecodeError:
            log.warning("stato non JSON: %r", payload[:120])
            return
        if not isinstance(st, dict):
            return
        self.state, self.state_ts = st, time.time()
        self.hub.publish("state", st)
        # chiusura di sicurezza del ciclo se la macchina va in allarme/emergenza senza evento
        s = st.get("st")
        if s in ("ALARM", "ESTOP"):
            open_ = self.db.open_cycle()
            if open_:
                self.db.end_cycle(open_["id"], "emergenza" if s == "ESTOP" else "allarme",
                                  st.get("alm", "") or s)
                self.hub.publish("history", None)

    def _on_resp(self, text: str) -> None:
        self.hub.publish("resp", text)
        parts = text.split()
        target = None
        with self._lock:
            if parts and parts[0].upper() == "OK" and len(parts) > 1:
                kw = parts[1].upper()
                for w in self._waiters:
                    if w[0] == kw and not w[2].done():
                        target = w
                        break
            if target is None:  # ERR (o OK senza parola chiave): primo in attesa (FIFO)
                target = next((w for w in self._waiters if not w[2].done()), None)
            if target:
                self._waiters.remove(target)
        if target:
            _, loop, fut = target
            loop.call_soon_threadsafe(_set_result, fut, text)

    def _on_event(self, text: str) -> None:
        ev = {"ts": time.time(), "text": text}
        self.events.append(ev)
        self.hub.publish("event", ev)
        parts = text.split()
        if not parts:
            return
        kw = parts[0].upper()
        changed = True
        if kw == "CYCLE_START":
            ctx = self._pending_run if self._pending_run and time.time() - self._pending_run["ts"] < 60 else None
            self._pending_run = None
            self.db.start_cycle(ctx and ctx.get("recipe_id"), ctx and ctx.get("recipe_name"),
                                ctx and ctx.get("run_line"), ctx and ctx.get("np"))
        elif kw == "PASS" and len(parts) > 1:
            open_ = self.db.open_cycle()
            try:
                k, np_ = (int(x) for x in parts[1].split("/"))
            except ValueError:
                k, np_ = None, None
            if open_ and k is not None:
                # "PASS k/np" = inizio della passata k: completate k-1
                self.db.update_cycle_pass(open_["id"], max(0, k - 1), np_)
            changed = False
        elif kw in ("CYCLE_DONE", "STOP", "STOPPED", "CYCLE_ABORT", "ALARM", "ESTOP"):
            open_ = self.db.open_cycle()
            if open_:
                if kw == "CYCLE_DONE":
                    self.db.update_cycle_pass(open_["id"], open_["np"] or open_["passes_done"], None)
                    self.db.end_cycle(open_["id"], "completato")
                elif kw in ("STOP", "STOPPED", "CYCLE_ABORT"):
                    self.db.end_cycle(open_["id"], "interrotto", "STOP")
                elif kw == "ALARM":
                    self.db.end_cycle(open_["id"], "allarme", " ".join(parts[1:]))
                else:
                    self.db.end_cycle(open_["id"], "emergenza", "ESTOP")
            else:
                changed = False
        else:
            changed = False
        if changed:
            self.hub.publish("history", None)

    # ------------------------------------------------------------ vista
    def snapshot(self) -> dict:
        age = time.time() - self.state_ts if self.state_ts else None
        return {"online": self.online, "mqtt": self.connected, "state": self.state,
                "age": round(age, 2) if age is not None else None}


def _set_result(fut: asyncio.Future, value: str) -> None:
    if not fut.done():
        fut.set_result(value)


def _safe_np(p: dict) -> int | None:
    try:
        return protocol.num_passes(p["g0"], p["g1"], p["dg"], p["n"])
    except (ValueError, KeyError):
        return None


class MqttLink(MachineLink):
    """Collegamento reale al broker con paho-mqtt v2 (loop in thread)."""

    def __init__(self, settings: Settings, db: Database, hub: Hub) -> None:
        super().__init__(settings, db, hub)
        import paho.mqtt.client as mqtt

        self._mqtt = mqtt
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=f"manipmasta-server-{int(time.time())}")
        if settings.mqtt_user:
            self.client.username_pw_set(settings.mqtt_user, settings.mqtt_pass or None)
        self.client.reconnect_delay_set(1, 15)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = lambda c, u, m: self.handle_message(m.topic, m.payload)

    def start(self) -> None:
        s = self.settings
        log.info("MQTT: connessione a %s:%s", s.mqtt_host, s.mqtt_port)
        self.client.connect_async(s.mqtt_host, s.mqtt_port, keepalive=30)
        self.client.loop_start()

    def stop(self) -> None:
        try:
            self.client.disconnect()
            self.client.loop_stop()
        except Exception:
            pass

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            log.error("MQTT: connessione rifiutata: %s", reason_code)
            return
        self.connected = True
        log.info("MQTT: connesso")
        for t in ("state", "event", "resp", "online"):
            client.subscribe(self.settings.topic(t), qos=1)
        self.hub.publish("mqtt", True)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        self.connected = False
        log.warning("MQTT: disconnesso (%s)", reason_code)
        self.hub.publish("mqtt", False)

    def _publish_cmd(self, line: str) -> bool:
        if not self.connected:
            return False
        info = self.client.publish(self.settings.topic("cmd"), line, qos=1)
        return info.rc == self._mqtt.MQTT_ERR_SUCCESS
