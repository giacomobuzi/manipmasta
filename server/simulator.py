#!/usr/bin/env python3
"""Simulatore dell'Arduino ManipMasta su MQTT (SPEC §3, §4).

Si comporta come il firmware: riceve i comandi su <prefix>/cmd, risponde su <prefix>/resp,
pubblica lo stato JSON (retained) su <prefix>/state ogni 200 ms in movimento e ogni 2 s a riposo,
gli eventi su <prefix>/event e la presenza su <prefix>/online (LWT "0").

Cinematica semplificata ma con le velocità/accelerazioni reali dei parametri (profilo trapezoidale);
--speed accelera il tempo simulato (es. --speed 20).

Topic solo-simulatore <prefix>/sim per provocare condizioni di guasto:
    ESTOP 1|0     catena di emergenza aperta/chiusa
    CURTAIN 1|0   barriera interrotta/libera
    SEAT 0|1      portale tolto/in sede
    ALM X|Z1|Z2|R allarme driver

Uso:
    python simulator.py --host localhost --user manipmasta --password xxx --speed 10
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import threading
import time

import paho.mqtt.client as mqtt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import protocol  # noqa: E402

FW = "1.0.0-sim"
log = logging.getLogger("sim")


class Abort(Exception):
    def __init__(self, hard: bool = False):
        super().__init__("abort")
        self.hard = hard


class Simulator:
    def __init__(self, client: mqtt.Client | None, prefix: str = "manipmasta", speed: float = 1.0,
                 tick: float = 0.02):
        self.client = client
        self.prefix = prefix
        self.speed = max(0.01, speed)
        self.tick = tick
        self.params = dict(protocol.PARAM_DEFAULTS)
        self.saved = dict(self.params)
        self.boot = time.time()
        # stato macchina
        self.st = "BOOT"
        self.hm = 0
        self.en = 0
        self.x = 123.0                 # posizione X non nota prima dell'homing
        self.z1, self.z2 = 61.3, 60.7  # gap per lato (prima dell'homing non allineati)
        self.r = 0.0
        self.cyc = {"pass": 0, "np": 0, "gap": 0.0}
        self.alm = ""
        self.inp = {"estop": 0, "curt": 0, "seat": 1}
        # controllo
        self.lock = threading.RLock()
        self.worker: threading.Thread | None = None
        self.abort: Abort | None = None
        self.pause_req = False
        self.resume_evt = threading.Event()
        self.kick = threading.Event()
        self.running = True

    # ------------------------------------------------------------------ util
    @property
    def g(self) -> float:
        return (self.z1 + self.z2) / 2

    def topic(self, name: str) -> str:
        return f"{self.prefix}/{name}"

    def pub(self, name: str, payload: str, retain: bool = False) -> None:
        if self.client:
            self.client.publish(self.topic(name), payload, qos=1 if name != "state" else 0, retain=retain)

    def resp(self, text: str) -> None:
        log.info("resp %s", text)
        self.pub("resp", text)

    def event(self, text: str) -> None:
        log.info("event %s", text)
        self.pub("event", text)
        self.kick.set()

    def busy(self) -> bool:
        return self.worker is not None and self.worker.is_alive()

    def state_dict(self) -> dict:
        p = self.params
        return {
            "st": self.st, "hm": self.hm, "en": self.en,
            "x": round(self.x, 2), "g": round(self.g, 2),
            "z1": round(self.z1, 2), "z2": round(self.z2, 2), "r": round(self.r, 1),
            "cyc": {"pass": self.cyc["pass"], "np": self.cyc["np"], "gap": round(self.cyc["gap"], 2)},
            "in": {
                "xmin": int(self.x <= p["x_min"] + 0.01),
                "xmax": int(self.x >= p["x_max"] + 5),
                "z1h": int(self.z1 >= p["z_home_gap"] - 0.01),
                "z2h": int(self.z2 >= p["z_home_gap"] - 0.01),
                "seat": self.inp["seat"], "estop": self.inp["estop"], "curt": self.inp["curt"],
            },
            "alm": self.alm, "fw": FW, "up": int((time.time() - self.boot) * 1000),
        }

    def publish_state(self) -> None:
        self.pub("state", json.dumps(self.state_dict(), separators=(",", ":")), retain=True)

    def state_loop(self) -> None:
        last = 0.0
        while self.running:
            moving = self.st in ("HOMING", "MOVING", "RUNNING")
            period = 0.2 if moving else 2.0
            if self.kick.wait(timeout=max(0.0, period - (time.time() - last))):
                self.kick.clear()
            self.publish_state()
            last = time.time()

    # ------------------------------------------------------------------ cinematica
    def _sleep(self) -> float:
        time.sleep(self.tick)
        return self.tick * self.speed

    def _check(self) -> None:
        if self.abort is not None:
            raise self.abort

    def _move(self, get, set_, target: float, vmax: float, acc: float, slave_r: bool = False,
              od: float = 0.0, interruptible: bool = True) -> None:
        """Movimento trapezoidale di un asse virtuale; STOP = decelerazione, guasto = stop immediato."""
        start = get()
        dist = target - start
        d = abs(dist)
        if d < 1e-6:
            return
        sgn = 1 if dist > 0 else -1
        d_acc = vmax * vmax / (2 * acc)
        if 2 * d_acc > d:  # triangolare
            vpk = math.sqrt(d * acc)
            ta, tc = vpk / acc, 0.0
        else:
            vpk = vmax
            ta, tc = vmax / acc, (d - 2 * d_acc) / vmax
        T = 2 * ta + tc

        def pos(t: float) -> tuple[float, float]:
            if t < ta:
                return 0.5 * acc * t * t, acc * t
            if t < ta + tc:
                return 0.5 * acc * ta * ta + vpk * (t - ta), vpk
            td = min(t, T) - ta - tc
            return 0.5 * acc * ta * ta + vpk * tc + vpk * td - 0.5 * acc * td * td, max(0.0, vpk - acc * td)

        t = 0.0
        prev = start
        while t < T:
            if interruptible and self.abort is not None:
                if self.abort.hard:
                    raise self.abort
                # STOP: rampa di decelerazione dalla velocità attuale
                _, v = pos(t)
                s0 = get()
                tt, tstop = 0.0, (v / acc if acc else 0)
                while tt < tstop:
                    tt = min(tstop, tt + self._sleep())
                    newp = s0 + sgn * (v * tt - 0.5 * acc * tt * tt)
                    if slave_r:
                        self.r += abs(newp - get()) * (1 + od / 100)
                    set_(newp)
                    if self.abort is not None and self.abort.hard:
                        break
                raise self.abort
            t = min(T, t + self._sleep())
            s, _ = pos(t)
            newp = start + sgn * s
            if slave_r:
                self.r += abs(newp - prev) * (1 + od / 100)
            prev = newp
            set_(newp)
        set_(target)

    def move_x(self, target: float, f: float | None = None, slave_r: bool = False, od: float = 0.0,
               acc: float | None = None) -> None:
        p = self.params
        v = min(f or p["x_vmax"], p["x_vmax"])
        self._move(lambda: self.x, lambda val: setattr(self, "x", val), target, v, acc or p["x_acc"],
                   slave_r=slave_r, od=od)

    def move_g(self, target: float, interruptible: bool = True) -> None:
        p = self.params
        off = self.z2 - self.z1

        def set_(val: float) -> None:
            self.z1, self.z2 = val - off / 2, val + off / 2

        self._move(lambda: self.g, set_, target, p["z_vmax"], p["z_acc"], interruptible=interruptible)

    def move_r(self, delta: float) -> None:
        self._move(lambda: self.r, lambda val: setattr(self, "r", val), self.r + delta, 50.0, 200.0)

    def after_move(self) -> None:
        """PAUSE: si ferma a fine movimento corrente con il rullo in quota."""
        self._check()
        if self.pause_req:
            prev = self.st
            self.st = "PAUSED"
            self.event("PAUSED")
            self.resume_evt.clear()
            while not self.resume_evt.wait(0.05):
                self._check()
            self._check()
            self.pause_req = False
            self.st = prev
            self.event("RESUMED")

    # ------------------------------------------------------------------ lavori
    def start_job(self, name: str, fn, *args) -> None:
        self.abort = None
        self.pause_req = False

        def run():
            try:
                fn(*args)
            except Abort as a:
                self._on_abort(a)
            except Exception:  # pragma: no cover
                log.exception("errore nel lavoro %s", name)
                self.st = "ALARM"
                self.alm = "SIM_ERR"
            finally:
                self.kick.set()

        self.worker = threading.Thread(target=run, name=name, daemon=True)
        self.worker.start()

    def _on_abort(self, a: Abort) -> None:
        if a.hard:
            return  # stato già impostato da chi ha causato il guasto
        # STOP (o barriera): Z sale a gap sicuro, ciclo annullato
        prev_alarm = self.st == "ALARM"
        self.abort = None
        if self.hm:
            try:
                safe = min(self.params["g_max"], self.g + protocol.SAFE_GAP_ADD)
                self.move_g(safe)
            except Abort:
                return
        if not prev_alarm:
            self.st = "READY" if self.hm else "IDLE"
        self.event("STOP")

    def job_home(self) -> None:
        p = self.params
        self.st = "HOMING"
        self.hm = 0
        self.kick.set()
        # Z: ogni lato sul proprio finecorsa alto (auto-livellamento)
        top = p["z_home_gap"]
        d1, d2 = top - self.z1, top - self.z2
        base1, base2 = self.z1, self.z2
        span = max(d1, d2, 0.001)
        prog = {"v": 0.0}

        def set_(val: float) -> None:
            prog["v"] = val
            self.z1 = min(top, base1 + val)
            self.z2 = min(top, base2 + val)

        self._move(lambda: prog["v"], set_, span, p["z_vmax"], p["z_acc"])
        self.z1 = self.z2 = top
        self.after_move()
        # X verso X_MIN a velocità ridotta, poi offset
        self.move_x(p["x_min"] - 2, f=p["x_vmax"] / 3)
        self.x = p["x_min"]
        self.after_move()
        self.move_x(p["x_min"] + p["x_home_off"], f=p["x_vmax"] / 3)
        self.hm = 1
        self.st = "READY"
        self.event("HOMED")

    def job_simple(self, kind: str, value: float, f: float | None = None) -> None:
        self.st = "MOVING"
        self.kick.set()
        if kind == "X":
            self.move_x(value, f)
        elif kind == "G":
            self.move_g(value)
        elif kind == "R":
            self.move_r(value)
        self.after_move()
        self.st = "READY" if self.hm else "IDLE"

    def job_run(self, prm: dict) -> None:
        p = self.params
        plan = protocol.pass_plan(prm)
        np_ = len(plan)
        cx, od, f = prm["cx"], prm["od"], prm["f"]
        M = protocol.RUN_MARGIN
        self.st = "RUNNING"
        self.cyc = {"pass": 0, "np": np_, "gap": prm["g0"]}
        self.event("CYCLE_START")
        # 2. approccio: Z a gap sicuro, X fuori impasto, Z a g0
        self.move_g(min(p["g_max"], prm["g0"] + protocol.SAFE_GAP_ADD))
        self.after_move()
        self.move_x(cx - prm["s0"] - M)
        self.after_move()
        self.move_g(prm["g0"])
        self.after_move()
        # 3-5. passate doppie
        for k, (g_fwd, g_back, s) in enumerate(plan, start=1):
            self.cyc = {"pass": k, "np": np_, "gap": g_fwd}
            self.event(f"PASS {k}/{np_}")
            a, b = cx - s - M, cx + s + M
            if abs(self.x - a) > 0.01:
                self.move_x(a, f)
                self.after_move()
            if abs(self.g - g_fwd) > 0.001:
                self.move_g(g_fwd)
            self.move_x(b, f, slave_r=True, od=od)        # passata avanti
            self.after_move()
            self.move_g(g_back)                             # nuovo gap fuori impasto
            self.cyc["gap"] = g_back
            self.after_move()
            self.move_x(a, f, slave_r=True, od=od)         # passata indietro
            self.after_move()
        self.move_g(prm["g1"] + protocol.END_GAP_ADD)
        self.after_move()
        self.move_x(cx)
        self.st = "READY"
        self.event("CYCLE_DONE")

    # ------------------------------------------------------------------ guasti (topic sim)
    def fault(self, st: str, alm: str, ev: str) -> None:
        self.abort = Abort(hard=True)
        self.st, self.alm, self.hm, self.en = st, alm, 0, 0
        self.resume_evt.set()
        self.event(ev)

    def on_sim(self, line: str) -> None:
        parts = line.strip().upper().split()
        if len(parts) != 2:
            return
        what, val = parts
        with self.lock:
            if what == "ESTOP":
                self.inp["estop"] = 1 if val == "1" else 0
                if val == "1":
                    self.fault("ESTOP", "ESTOP", "ESTOP")
            elif what == "CURTAIN":
                self.inp["curt"] = 1 if val == "1" else 0
                if val == "1" and self.st in ("HOMING", "MOVING", "RUNNING", "PAUSED"):
                    self.abort = Abort(hard=False)
                    self.resume_evt.set()
                    self.st, self.alm = "ALARM", "CURTAIN"
                    self.event("ALARM CURTAIN")
            elif what == "SEAT":
                self.inp["seat"] = 0 if val == "0" else 1
                if val == "0":
                    self.fault("ALARM", "SEAT", "ALARM SEAT")
            elif what == "ALM" and val in ("X", "Z1", "Z2", "R"):
                self.fault("ALARM", f"{val}_ALM", f"ALARM {val}_ALM")
        self.kick.set()

    # ------------------------------------------------------------------ comandi
    def on_cmd(self, line: str) -> None:
        line = line.strip()
        if not line:
            return
        log.info("cmd  %s", line)
        with self.lock:
            out = self._cmd(line)
        if out:
            self.resp(out)
        self.kick.set()

    def _motion_check(self, need_home: bool = True) -> str | None:
        if self.inp["estop"] or self.st == "ESTOP":
            return "ERR E07 emergenza attiva"
        if self.st == "ALARM":
            return "ERR E08 allarme driver" if self.alm.endswith("_ALM") else f"ERR E04 allarme {self.alm}"
        if not self.inp["seat"]:
            return "ERR E06 portale non in sede"
        if self.busy():
            return f"ERR E04 stato {self.st} non consente"
        if not self.en:
            return "ERR E04 driver disabilitati (ENABLE 1)"
        if need_home and not self.hm:
            return "ERR E03 non homed"
        return None

    def _cmd(self, line: str) -> str | None:
        parts = line.split()
        kw, args = parts[0].upper(), parts[1:]
        p = self.params
        if kw == "PING":
            return "OK PING"
        if kw == "STATUS":
            self.publish_state()
            return "OK STATUS"
        if kw == "ENABLE":
            if len(args) != 1 or args[0] not in ("0", "1"):
                return "ERR E02 uso: ENABLE 1|0"
            if args[0] == "1":
                if self.inp["estop"] or self.st == "ESTOP":
                    return "ERR E07 emergenza attiva"
                self.en = 1
            else:
                if self.busy():
                    return "ERR E04 in movimento"
                self.en = 0
            return "OK ENABLE"
        if kw == "HOME":
            err = self._motion_check(need_home=False)
            if err:
                return err
            self.start_job("home", self.job_home)
            return "OK HOME"
        if kw in ("JOG", "MOVE", "GAP"):
            try:
                if kw == "GAP":
                    axis, val, f = "G", float(args[0]), None
                    if len(args) != 1:
                        raise ValueError
                else:
                    axis, val = args[0].upper(), float(args[1])
                    f = None
                    if kw == "MOVE":
                        if axis != "X" or len(args) not in (2, 4):
                            raise ValueError
                        if len(args) == 4:
                            if args[2].upper() != "F":
                                raise ValueError
                            f = float(args[3])
                    elif axis not in ("X", "G", "R") or len(args) != 2:
                        raise ValueError
            except (ValueError, IndexError):
                return "ERR E02 parametro non valido"
            err = self._motion_check(need_home=axis != "R")
            if err:
                return err
            if axis == "R":
                self.start_job("jog", self.job_simple, "R", val)
                return f"OK {kw}"
            if kw == "JOG":
                target = (self.x if axis == "X" else self.g) + val
            else:
                target = val
            lo, hi = (p["x_min"], p["x_max"]) if axis == "X" else (p["g_min"], p["g_max"])
            if not (lo - 1e-6 <= target <= hi + 1e-6):
                return f"ERR E05 fuori limiti ({protocol.fmt(lo)}..{protocol.fmt(hi)})"
            if f is not None and not (0 < f <= p["x_vmax"]):
                return "ERR E02 velocità non valida"
            self.start_job(kw.lower(), self.job_simple, axis, target, f)
            return f"OK {kw}"
        if kw == "RUN":
            try:
                prm = protocol.run_params({"od": p["od"], **protocol.parse_run_args(args)})
            except protocol.CommandError as e:
                return f"ERR E02 {e}"
            err = self._motion_check()
            if err:
                return err
            if self.inp["curt"]:
                return "ERR E04 barriera interrotta"
            lim = protocol.run_limits_error(prm, p)
            if lim:
                return f"ERR E05 {lim}"
            self.start_job("run", self.job_run, prm)
            return "OK RUN"
        if kw == "PAUSE":
            if self.st != "RUNNING":
                return "ERR E04 nessun ciclo in corso"
            self.pause_req = True
            return "OK PAUSE"
        if kw == "RESUME":
            if self.st != "PAUSED" and not self.pause_req:
                return "ERR E04 non in pausa"
            if self.st != "PAUSED":
                self.pause_req = False
            self.resume_evt.set()
            return "OK RESUME"
        if kw == "STOP":
            if self.busy():
                self.abort = Abort(hard=False)
                self.resume_evt.set()
            return "OK STOP"
        if kw == "RESET":
            if self.inp["estop"]:
                return "ERR E07 emergenza attiva"
            if not self.inp["seat"]:
                return "ERR E06 portale non in sede"
            if self.inp["curt"]:
                return "ERR E04 barriera interrotta"
            if self.busy():
                return "ERR E04 in movimento"
            self.alm = ""
            if self.st in ("ALARM", "ESTOP", "IDLE", "READY", "BOOT"):
                self.st = "READY" if self.hm else "IDLE"
            self.event("RESET")
            return "OK RESET"
        if kw == "SET":
            if len(args) != 2 or args[0].lower() not in p:
                return "ERR E02 chiave sconosciuta"
            k, v = args[0].lower(), args[1]
            if self.busy():
                return "ERR E04 in movimento"
            try:
                if k in protocol.STR_KEYS or k in protocol.IP_KEYS:
                    val: object = v
                elif k in protocol.INT_KEYS:
                    val = int(v)
                else:
                    val = float(v)
            except ValueError:
                return "ERR E02 valore non valido"
            p[k] = val
            return f"OK SET {k} {self._val(k)}"
        if kw == "GET":
            if len(args) != 1 or args[0].lower() not in p:
                return "ERR E02 chiave sconosciuta"
            k = args[0].lower()
            return f"OK GET {k} {self._val(k)}"
        if kw == "SAVE":
            self.saved = dict(p)
            return "OK SAVE"
        if kw == "DEFAULTS":
            if self.busy():
                return "ERR E04 in movimento"
            self.params = dict(protocol.PARAM_DEFAULTS)
            return "OK DEFAULTS"
        return f"ERR E01 comando sconosciuto {kw}"

    def _val(self, k: str) -> str:
        v = self.params[k]
        if k == "mqtt_pass":
            return "***" if v else "-"
        if isinstance(v, float):
            return f"{v:.3f}".rstrip("0").rstrip(".") if not v.is_integer() else f"{v:.1f}"
        return str(v)

    def boot_done(self) -> None:
        self.st = "IDLE"
        self.en = 1
        self.event("BOOT")
        self.kick.set()


def main() -> None:
    ap = argparse.ArgumentParser(description="Simulatore Arduino ManipMasta su MQTT")
    ap.add_argument("--host", default=os.environ.get("MQTT_HOST", "localhost"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("MQTT_PORT", "1883")))
    ap.add_argument("--user", default=os.environ.get("SIM_MQTT_USER", os.environ.get("MQTT_DEVICE_USER", "")))
    ap.add_argument("--password", default=os.environ.get("SIM_MQTT_PASS", os.environ.get("MQTT_DEVICE_PASS", "")))
    ap.add_argument("--prefix", default=os.environ.get("TOPIC_PREFIX", "manipmasta"))
    ap.add_argument("--speed", type=float, default=float(os.environ.get("SIM_SPEED", "1")),
                    help="fattore di accelerazione del tempo (1 = reale)")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO if a.verbose else logging.WARNING,
                        format="%(asctime)s sim %(message)s")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"manipmasta-sim-{os.getpid()}")
    if a.user:
        client.username_pw_set(a.user, a.password or None)
    client.will_set(f"{a.prefix}/online", "0", qos=1, retain=True)
    sim = Simulator(client, a.prefix, a.speed)

    def on_connect(c, u, flags, rc, props):
        if rc.is_failure:
            print(f"connessione MQTT rifiutata: {rc}", file=sys.stderr)
            return
        c.subscribe(f"{a.prefix}/cmd", qos=1)
        c.subscribe(f"{a.prefix}/sim", qos=1)
        c.publish(f"{a.prefix}/online", "1", qos=1, retain=True)
        sim.kick.set()
        print(f"simulatore connesso a {a.host}:{a.port} (speed x{a.speed})", flush=True)

    def on_message(c, u, m):
        txt = m.payload.decode("utf-8", "replace")
        if m.topic.endswith("/sim"):
            sim.on_sim(txt)
        else:
            sim.on_cmd(txt)

    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(1, 10)
    client.connect_async(a.host, a.port, keepalive=15)
    client.loop_start()
    threading.Thread(target=sim.state_loop, daemon=True).start()
    time.sleep(0.5)
    sim.boot_done()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        sim.running = False
        client.publish(f"{a.prefix}/online", "0", qos=1, retain=True).wait_for_publish(2)
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
