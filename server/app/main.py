"""ManipMasta server: FastAPI + MQTT + SQLite (SPEC §5)."""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from . import protocol
from .bridge import Hub, MachineLink, MqttLink
from .config import Settings
from .db import Database

VERSION = "1.0.0"
STATIC_DIR = Path(__file__).parent / "static"
log = logging.getLogger("manipmasta")


# ------------------------------------------------------------------ modelli
class CmdIn(BaseModel):
    cmd: str = Field(..., max_length=200)


class RecipeIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    cx: float = 0
    s0: float = Field(150, gt=0)
    s1: float = Field(300, gt=0)
    g0: float = Field(40, gt=0)
    g1: float = Field(5, gt=0)
    dg: float = Field(3, gt=0)
    f: float = Field(60, gt=0)
    n: int = Field(2, ge=0, le=50)
    od: float = Field(2.0, ge=0, le=20)
    note: str = Field("", max_length=2000)

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("nome obbligatorio")
        return v

    @model_validator(mode="after")
    def _limits(self):
        err = protocol.run_limits_error(self.model_dump())
        if err:
            raise ValueError(err)
        return self


def recipe_out(r: dict) -> dict:
    p = {k: r[k] for k in protocol.RUN_KEYS}
    r = dict(r)
    r["np"] = protocol.num_passes(p["g0"], p["g1"], p["dg"], p["n"])
    r["t_est"] = round(protocol.estimate_seconds(p))
    r["run_line"] = protocol.build_run_line(p)
    return r


# ------------------------------------------------------------------ app
def create_app(settings: Settings | None = None, link: MachineLink | None = None,
               db: Database | None = None) -> FastAPI:
    settings = settings or Settings()
    db = db or Database(settings.db_path)
    hub = link.hub if link else Hub()
    link = link or MqttLink(settings, db, hub)
    if not settings.api_token:
        log.warning("API_TOKEN non impostato: tutte le API protette risponderanno 401")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        hub.bind(asyncio.get_running_loop())
        link.start()
        yield
        link.stop()

    app = FastAPI(title="ManipMasta", version=VERSION, lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.state.settings, app.state.db, app.state.link, app.state.hub = settings, db, link, hub

    def check_token(token: str | None) -> bool:
        return bool(settings.api_token) and token is not None and \
            hmac.compare_digest(token.encode(), settings.api_token.encode())

    async def auth(request: Request) -> None:
        h = request.headers.get("authorization", "")
        token = h[7:].strip() if h.lower().startswith("bearer ") else None
        if not check_token(token):
            raise HTTPException(401, "token mancante o non valido",
                                headers={"WWW-Authenticate": "Bearer"})

    A = [Depends(auth)]

    # ---------------------------------------------------------- API
    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": VERSION, "mqtt": link.connected, "online": link.online}

    @app.get("/api/state", dependencies=A)
    def get_state():
        return link.snapshot()

    @app.get("/api/events", dependencies=A)
    def get_events(limit: int = Query(100, ge=1, le=300)):
        return list(link.events)[-limit:][::-1]

    @app.post("/api/cmd", dependencies=A)
    async def post_cmd(body: CmdIn):
        try:
            line = protocol.validate_command(body.cmd)
        except protocol.CommandError as e:
            raise HTTPException(400, str(e))
        res = await link.send(line)
        if not res["sent"]:
            raise HTTPException(503, "broker MQTT non connesso: comando non inviato")
        return res

    @app.get("/api/recipes", dependencies=A)
    def list_recipes():
        return [recipe_out(r) for r in db.list_recipes()]

    @app.post("/api/recipes", dependencies=A, status_code=201)
    def create_recipe(body: RecipeIn):
        return recipe_out(db.create_recipe(body.model_dump()))

    @app.get("/api/recipes/{rid}", dependencies=A)
    def get_recipe(rid: int):
        r = db.get_recipe(rid)
        if not r:
            raise HTTPException(404, "ricetta non trovata")
        return recipe_out(r)

    @app.put("/api/recipes/{rid}", dependencies=A)
    def update_recipe(rid: int, body: RecipeIn):
        r = db.update_recipe(rid, body.model_dump())
        if not r:
            raise HTTPException(404, "ricetta non trovata")
        return recipe_out(r)

    @app.delete("/api/recipes/{rid}", dependencies=A, status_code=204)
    def delete_recipe(rid: int):
        if not db.delete_recipe(rid):
            raise HTTPException(404, "ricetta non trovata")

    @app.post("/api/recipes/{rid}/run", dependencies=A)
    async def run_recipe(rid: int):
        r = db.get_recipe(rid)
        if not r:
            raise HTTPException(404, "ricetta non trovata")
        ro = recipe_out(r)
        line = protocol.validate_command(ro["run_line"])
        res = await link.send(line, run_ctx={"recipe_id": rid, "recipe_name": r["name"], "np": ro["np"]})
        if not res["sent"]:
            raise HTTPException(503, "broker MQTT non connesso: comando non inviato")
        return {**res, "np": ro["np"], "t_est": ro["t_est"]}

    @app.get("/api/history", dependencies=A)
    def history(limit: int = Query(50, ge=1, le=500)):
        return db.list_history(limit)

    @app.get("/api/params/keys", dependencies=A)
    def param_keys():
        return {"defaults": protocol.PARAM_DEFAULTS, "run_defaults": protocol.RUN_DEFAULTS}

    # ---------------------------------------------------------- WebSocket
    @app.websocket("/ws")
    async def ws(websocket: WebSocket, token: str | None = Query(None)):
        if not check_token(token):
            await websocket.close(code=4401)
            return
        await websocket.accept()
        q = hub.subscribe()
        try:
            await websocket.send_text(json.dumps({"type": "online", "data": link.online}))
            await websocket.send_text(json.dumps({"type": "mqtt", "data": link.connected}))
            if link.state is not None:
                await websocket.send_text(json.dumps({"type": "state", "data": link.state}))

            async def pump_out():
                while True:
                    msg = await q.get()
                    await websocket.send_text(json.dumps(msg))

            async def pump_in():  # keepalive dal client ("ping") e rilevazione chiusura
                while True:
                    txt = await websocket.receive_text()
                    if txt == "ping":
                        await websocket.send_text('{"type":"pong","data":null}')

            tasks = [asyncio.create_task(pump_out()), asyncio.create_task(pump_in())]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            hub.unsubscribe(q)

    # ---------------------------------------------------------- UI statica
    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    @app.get("/sw.js", include_in_schema=False)
    def sw():  # servito dalla radice per avere scope "/"
        return FileResponse(STATIC_DIR / "sw.js", media_type="text/javascript",
                            headers={"Cache-Control": "no-cache"})

    @app.get("/manifest.json", include_in_schema=False)
    def manifest():
        return FileResponse(STATIC_DIR / "manifest.json", media_type="application/manifest+json")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# Avvio: uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8080
