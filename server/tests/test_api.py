"""Test delle API con un collegamento MQTT finto (nessun broker)."""
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.bridge import Hub, MachineLink
from app.config import Settings
from app.db import Database
from app.main import create_app

TOKEN = "t0ken-di-prova"
H = {"Authorization": f"Bearer {TOKEN}"}


class FakeLink(MachineLink):
    """Finto Arduino: risponde OK ai comandi (o tace se reply=False)."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.sent: list[str] = []
        self.reply = True
        self.connected = True

    def start(self):
        self.handle_message("manipmasta/online", b"1")

    def stop(self):
        pass

    def _publish_cmd(self, line):
        if not self.connected:
            return False
        self.sent.append(line)
        if self.reply:
            kw = line.split()[0]
            if kw == "GET":
                resp = f"OK GET {line.split()[1]} 16.0"
            elif kw == "HOME" and getattr(self, "fail_home", False):
                resp = "ERR E06 portale non in sede"
            else:
                resp = f"OK {kw}"
            # risposta da un altro thread, come paho
            import threading
            threading.Timer(0.01, self.handle_message, ("manipmasta/resp", resp.encode())).start()
        return True


@pytest.fixture()
def env(tmp_path):
    s = Settings(api_token=TOKEN, db_path=str(tmp_path / "t.db"), resp_timeout=0.5)
    db = Database(s.db_path)
    link = FakeLink(s, db, Hub())
    app = create_app(s, link, db)
    with TestClient(app) as c:
        yield c, link, db


def test_health_without_auth(env):
    c, link, _ = env
    r = c.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


@pytest.mark.parametrize("path", ["/api/state", "/api/recipes", "/api/history"])
def test_auth_required(env, path):
    c, *_ = env
    assert c.get(path).status_code == 401
    assert c.get(path, headers={"Authorization": "Bearer sbagliato"}).status_code == 401
    assert c.get(path, headers=H).status_code == 200


def test_empty_token_refuses_everything(tmp_path):
    s = Settings(api_token="", db_path=str(tmp_path / "x.db"))
    db = Database(s.db_path)
    app = create_app(s, FakeLink(s, db, Hub()), db)
    with TestClient(app) as c:
        assert c.get("/api/state", headers={"Authorization": "Bearer "}).status_code == 401


def test_ui_served(env):
    c, *_ = env
    r = c.get("/")
    assert r.status_code == 200 and "ManipMasta" in r.text
    assert c.get("/static/app.js").status_code == 200
    assert c.get("/manifest.json").json()["short_name"] == "ManipMasta"
    assert c.get("/sw.js").status_code == 200


def test_cmd_whitelist_and_response(env):
    c, link, _ = env
    r = c.post("/api/cmd", json={"cmd": "home"}, headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["cmd"] == "HOME" and body["resp"] == "OK HOME" and body["ok"] is True
    assert link.sent[-1] == "HOME"

    r = c.post("/api/cmd", json={"cmd": "rm -rf /"}, headers=H)
    assert r.status_code == 400 and "non ammesso" in r.json()["detail"]
    r = c.post("/api/cmd", json={"cmd": "JOG Q 4"}, headers=H)
    assert r.status_code == 400
    assert link.sent == ["HOME"]


def test_cmd_error_response(env):
    c, link, _ = env
    link.fail_home = True
    body = c.post("/api/cmd", json={"cmd": "HOME"}, headers=H).json()
    assert body["ok"] is False and body["resp"].startswith("ERR E06")


def test_cmd_get_returns_value(env):
    c, *_ = env
    body = c.post("/api/cmd", json={"cmd": "GET x_spm"}, headers=H).json()
    assert body["resp"] == "OK GET x_spm 16.0"


def test_cmd_timeout(env):
    c, link, _ = env
    link.reply = False
    t = time.time()
    body = c.post("/api/cmd", json={"cmd": "PING"}, headers=H).json()
    assert body["timeout"] is True and body["resp"] is None and body["sent"] is True
    assert time.time() - t < 2


def test_cmd_broker_down(env):
    c, link, _ = env
    link.connected = False
    assert c.post("/api/cmd", json={"cmd": "PING"}, headers=H).status_code == 503


def test_state_cache(env):
    c, link, _ = env
    st = {"st": "READY", "hm": 1, "en": 1, "x": 1.5, "g": 40.0, "cyc": {"pass": 0, "np": 0, "gap": 0}}
    link.handle_message("manipmasta/state", json.dumps(st).encode())
    body = c.get("/api/state", headers=H).json()
    assert body["online"] is True and body["state"]["x"] == 1.5
    link.handle_message("manipmasta/state", b"non json")  # ignorato
    assert c.get("/api/state", headers=H).json()["state"]["st"] == "READY"


def test_recipes_seed_and_crud(env):
    c, *_ = env
    rs = c.get("/api/recipes", headers=H).json()
    names = {r["name"] for r in rs}
    assert {"Frolla 5 mm", "Sfoglia 3 mm", "Pasta biscotti 8 mm"} <= names
    frolla = next(r for r in rs if r["name"] == "Frolla 5 mm")
    assert frolla["np"] == 14 and frolla["t_est"] > 0
    assert frolla["run_line"] == "RUN cx=0 s0=150 s1=300 g0=40 g1=5 dg=3 f=60 n=2 od=2"

    new = dict(name="Test 4 mm", cx=0, s0=150, s1=250, g0=30, g1=4, dg=2, f=50, n=1, od=2, note="x")
    r = c.post("/api/recipes", json=new, headers=H)
    assert r.status_code == 201
    rid = r.json()["id"]
    assert r.json()["np"] == 14
    new["g1"] = 6
    r = c.put(f"/api/recipes/{rid}", json=new, headers=H)
    assert r.status_code == 200 and r.json()["g1"] == 6
    assert c.get(f"/api/recipes/{rid}", headers=H).json()["name"] == "Test 4 mm"
    assert c.delete(f"/api/recipes/{rid}", headers=H).status_code == 204
    assert c.get(f"/api/recipes/{rid}", headers=H).status_code == 404
    assert c.put("/api/recipes/9999", json=new, headers=H).status_code == 404


@pytest.mark.parametrize("patch", [{"g0": 3, "g1": 5}, {"cx": 600}, {"f": 999}, {"dg": 0}, {"name": "  "}, {"n": -1}])
def test_recipe_validation(env, patch):
    c, *_ = env
    body = dict(name="X", cx=0, s0=150, s1=300, g0=40, g1=5, dg=3, f=60, n=2, od=2)
    body.update(patch)
    assert c.post("/api/recipes", json=body, headers=H).status_code == 422


def test_seed_only_once(tmp_path):
    p = str(tmp_path / "s.db")
    db = Database(p)
    for r in db.list_recipes():
        db.delete_recipe(r["id"])
    db.close()
    assert Database(p).list_recipes() == []


def test_run_recipe_and_history(env):
    c, link, db = env
    rid = next(r["id"] for r in c.get("/api/recipes", headers=H).json() if r["name"] == "Frolla 5 mm")
    body = c.post(f"/api/recipes/{rid}/run", headers=H).json()
    assert body["ok"] and body["np"] == 14
    assert link.sent[-1] == "RUN cx=0 s0=150 s1=300 g0=40 g1=5 dg=3 f=60 n=2 od=2"

    link.handle_message("manipmasta/event", b"CYCLE_START")
    link.handle_message("manipmasta/event", b"PASS 1/14")
    link.handle_message("manipmasta/event", b"PASS 5/14")
    h = c.get("/api/history", headers=H).json()
    assert h[0]["outcome"] == "in corso" and h[0]["recipe_name"] == "Frolla 5 mm" and h[0]["passes_done"] == 4
    link.handle_message("manipmasta/event", b"CYCLE_DONE")
    h = c.get("/api/history", headers=H).json()[0]
    assert h["outcome"] == "completato" and h["passes_done"] == 14 and h["duration_s"] >= 0


def test_history_outcomes(env):
    c, link, _ = env
    for ev, outcome in [(b"STOP", "interrotto"), (b"ALARM X_ALM", "allarme"), (b"ESTOP", "emergenza")]:
        c.post("/api/cmd", json={"cmd": "RUN g0=20 g1=5"}, headers=H)
        link.handle_message("manipmasta/event", b"CYCLE_START")
        link.handle_message("manipmasta/event", ev)
        h = c.get("/api/history", headers=H).json()[0]
        assert h["outcome"] == outcome
        assert h["recipe_name"] is None and h["run_line"] == "RUN g0=20 g1=5" and h["np"] == 7
    assert c.get("/api/history", headers=H).json()[0]["detail"] == "ESTOP"
    assert c.get("/api/history", headers=H).json()[1]["detail"] == "X_ALM"


def test_events_endpoint(env):
    c, link, _ = env
    link.handle_message("manipmasta/event", b"HOMED")
    ev = c.get("/api/events", headers=H).json()
    assert ev[0]["text"] == "HOMED"


def test_websocket(env):
    c, link, _ = env
    with pytest.raises(Exception):
        with c.websocket_connect("/ws?token=no") as ws:
            ws.receive_text()
    with c.websocket_connect(f"/ws?token={TOKEN}") as ws:
        first = json.loads(ws.receive_text())
        assert first == {"type": "online", "data": True}
        assert json.loads(ws.receive_text())["type"] == "mqtt"
        link.handle_message("manipmasta/state", json.dumps({"st": "IDLE"}).encode())
        link.handle_message("manipmasta/event", b"BOOT")
        link.handle_message("manipmasta/resp", b"OK PING")
        got = [json.loads(ws.receive_text()) for _ in range(3)]
        assert [m["type"] for m in got] == ["state", "event", "resp"]
        assert got[0]["data"]["st"] == "IDLE" and got[1]["data"]["text"] == "BOOT" and got[2]["data"] == "OK PING"
        ws.send_text("ping")
        assert json.loads(ws.receive_text())["type"] == "pong"
