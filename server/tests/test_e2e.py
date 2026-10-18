"""Prova end-to-end: Mosquitto reale (config e ACL del progetto) + simulatore + server.

Richiede il binario `mosquitto` (apt install mosquitto); altrimenti il test è saltato.
"""
import os
import shutil
import socket
import subprocess
import sys
import time

import pytest
from fastapi.testclient import TestClient

from app.bridge import Hub, MqttLink
from app.config import Settings
from app.db import Database
from app.main import create_app

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOSQ = shutil.which("mosquitto") or "/usr/sbin/mosquitto"
MOSQ_PASSWD = shutil.which("mosquitto_passwd")
pytestmark = pytest.mark.skipif(not (os.path.exists(MOSQ) and MOSQ_PASSWD), reason="mosquitto non installato")

TOKEN = "e2e-token"
H = {"Authorization": f"Bearer {TOKEN}"}


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture(scope="module")
def stack(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("e2e")
    port = free_port()
    # config del progetto, con percorsi e porta adattati al test
    conf = open(os.path.join(SERVER_DIR, "mosquitto/config/mosquitto.conf")).read()
    conf = (conf.replace("/mosquitto/config/", f"{tmp}/").replace("/mosquitto/data/", f"{tmp}/")
                .replace("listener 1883", f"listener {port} 127.0.0.1"))
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        conf += "\nuser root\n"  # altrimenti mosquitto passa all'utente 'mosquitto' e non legge tmp
    (tmp / "mosquitto.conf").write_text(conf)
    shutil.copy(os.path.join(SERVER_DIR, "mosquitto/config/acl"), tmp / "acl")
    pw = tmp / "passwd"
    pw.touch()
    pw.chmod(0o600)
    for u, p in (("manipmasta-server", "srvpw"), ("manipmasta", "devpw"), ("manipmasta-tools", "toolpw")):
        subprocess.run([MOSQ_PASSWD, "-b", str(pw), u, p], check=True, capture_output=True)
    broker = subprocess.Popen([MOSQ, "-c", str(tmp / "mosquitto.conf")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(0.5)
    sim = subprocess.Popen([sys.executable, os.path.join(SERVER_DIR, "simulator.py"), "--port", str(port),
                            "--user", "manipmasta", "--password", "devpw", "--speed", "60"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    s = Settings(mqtt_host="127.0.0.1", mqtt_port=port, mqtt_user="manipmasta-server", mqtt_pass="srvpw",
                 api_token=TOKEN, db_path=str(tmp / "e2e.db"))
    db = Database(s.db_path)
    link = MqttLink(s, db, Hub())
    app = create_app(s, link, db)
    with TestClient(app) as c:
        yield c, link, port, tmp
    sim.terminate()
    broker.terminate()
    sim.wait(5)
    broker.wait(5)


def wait_for(fn, timeout=20.0, step=0.1):
    t = time.time()
    while time.time() - t < timeout:
        v = fn()
        if v:
            return v
        time.sleep(step)
    raise AssertionError("timeout")


def state(c):
    return c.get("/api/state", headers=H).json()


def cmd(c, line):
    return c.post("/api/cmd", json={"cmd": line}, headers=H).json()


def test_online_and_ping(stack):
    c, link, *_ = stack
    wait_for(lambda: state(c)["online"] and state(c)["state"])
    assert cmd(c, "PING")["resp"] == "OK PING"
    assert c.get("/api/health").json()["mqtt"] is True


def test_errors_before_homing(stack):
    c, *_ = stack
    wait_for(lambda: (state(c)["state"] or {}).get("st") == "IDLE")
    assert cmd(c, "JOG X 10")["resp"].startswith("ERR E03")
    assert cmd(c, "RUN")["resp"].startswith("ERR E03")
    assert cmd(c, "PAUSE")["resp"].startswith("ERR E04")
    assert cmd(c, "GET x_spm")["resp"] == "OK GET x_spm 16.0"


def test_home_jog_and_limits(stack):
    c, *_ = stack
    assert cmd(c, "HOME")["ok"]
    st = wait_for(lambda: (s := state(c)["state"]) and s["st"] == "READY" and s["hm"] == 1 and s)
    assert st["x"] == pytest.approx(-680, abs=0.01) and st["g"] == pytest.approx(150)
    assert cmd(c, "MOVE X 0 F 150")["ok"]
    wait_for(lambda: state(c)["state"]["st"] == "READY" and abs(state(c)["state"]["x"]) < 0.01)
    assert cmd(c, "JOG G -10")["ok"]
    wait_for(lambda: state(c)["state"]["st"] == "READY" and abs(state(c)["state"]["g"] - 140) < 0.01)
    assert cmd(c, "MOVE X 900")["resp"].startswith("ERR E05")
    assert cmd(c, "GAP 0.1")["resp"].startswith("ERR E05")


def test_run_recipe_full_cycle(stack):
    c, *_ = stack
    rid = next(r["id"] for r in c.get("/api/recipes", headers=H).json() if r["name"] == "Pasta biscotti 8 mm")
    res = c.post(f"/api/recipes/{rid}/run", headers=H).json()
    assert res["ok"], res
    wait_for(lambda: state(c)["state"]["st"] == "RUNNING", 5)
    wait_for(lambda: state(c)["state"]["st"] == "READY", 30)
    h = c.get("/api/history", headers=H).json()[0]
    assert h["outcome"] == "completato" and h["recipe_name"] == "Pasta biscotti 8 mm"
    assert h["passes_done"] == h["np"] == 11
    st = state(c)["state"]
    assert st["x"] == pytest.approx(0, abs=0.01) and st["g"] == pytest.approx(8 + 30, abs=0.01)
    # durata simulata coerente con la stima (speed 60)
    est = res["t_est"]
    assert 0.6 * est < h["duration_s"] * 60 < 1.6 * est


def test_pause_resume_stop(stack):
    c, *_ = stack
    assert cmd(c, "RUN g0=40 g1=5 dg=1 f=40")["ok"]
    wait_for(lambda: state(c)["state"]["st"] == "RUNNING", 5)
    assert cmd(c, "PAUSE")["ok"]
    wait_for(lambda: state(c)["state"]["st"] == "PAUSED", 10)
    g = state(c)["state"]["g"]
    time.sleep(0.5)
    assert state(c)["state"]["g"] == g          # in pausa il rullo resta in quota
    assert cmd(c, "RESUME")["ok"]
    wait_for(lambda: state(c)["state"]["st"] == "RUNNING", 5)
    assert cmd(c, "STOP")["ok"]
    wait_for(lambda: state(c)["state"]["st"] == "READY", 10)
    h = c.get("/api/history", headers=H).json()[0]
    assert h["outcome"] == "interrotto" and h["recipe_name"] is None


def test_estop_via_sim_topic(stack):
    c, link, port, _ = stack
    import paho.mqtt.publish as publish
    auth = {"username": "manipmasta-server", "password": "srvpw"}

    def sim(msg):
        # guasti simulati: solo l'utente di diagnostica può scrivere su /sim (ACL)
        publish.single("manipmasta/sim", msg, hostname="127.0.0.1", port=port,
                       auth={"username": "manipmasta-tools", "password": "toolpw"})

    # ACL: l'utente server non può falsificare lo stato
    publish.single("manipmasta/state", '{"st":"FAKE"}', hostname="127.0.0.1", port=port, auth=auth)
    time.sleep(0.3)
    assert state(c)["state"]["st"] != "FAKE"

    # ACL: l'utente server non può scrivere su /sim
    publish.single("manipmasta/sim", "ESTOP 1", hostname="127.0.0.1", port=port, auth=auth)
    time.sleep(0.3)
    assert state(c)["state"]["st"] != "ESTOP"

    sim("ESTOP 1")
    wait_for(lambda: state(c)["state"]["st"] == "ESTOP", 5)
    assert state(c)["state"]["in"]["estop"] == 1
    assert cmd(c, "HOME")["resp"].startswith("ERR E07")
    assert cmd(c, "RESET")["resp"].startswith("ERR E07")
    sim("ESTOP 0")
    time.sleep(0.3)
    assert cmd(c, "RESET")["ok"]
    wait_for(lambda: state(c)["state"]["st"] == "IDLE", 5)   # dopo emergenza serve un nuovo homing
    assert cmd(c, "ENABLE 1")["ok"]
    assert cmd(c, "HOME")["ok"]
    wait_for(lambda: state(c)["state"]["st"] == "READY", 20)
