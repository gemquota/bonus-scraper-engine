import json
from pathlib import Path
import configparser
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()
conns = []
PAUSED = False
STOPPED = False
IS_RUNNING = False


def _load_config():
    cfg = configparser.ConfigParser()
    cfg.read([str(Path("in/config.ini")), str(Path("in/config/config.ini"))])
    return {s: dict(cfg[s]) for s in cfg.sections()}


def _save_config(data: dict):
    cfg = configparser.ConfigParser()
    cfg.read([str(Path("in/config.ini")), str(Path("in/config/config.ini"))])
    for section, keys in data.items():
        if section not in cfg:
            cfg[section] = {}
        for k, v in keys.items():
            cfg[section][k] = str(v)
    p = Path("in/config/config.ini")
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        cfg.write(f)


@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    conns.append(ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        if ws in conns:
            conns.remove(ws)


@app.get("/api/config")
async def get_config():
    return _load_config()


@app.post("/api/config")
async def post_config(data: dict):
    _save_config(data)
    return {"status": "ok"}


@app.get("/api/status")
async def get_status():
    return {"paused": PAUSED, "stopped": STOPPED, "is_running": IS_RUNNING}


@app.post("/update")
async def update(data: dict):
    for c in conns:
        try:
            await c.send_text(json.dumps(data))
        except:
            pass
    return {"status": "ok"}


@app.post("/api/control/pause")
async def control_pause():
    global PAUSED
    PAUSED = True
    return {"status": "paused"}


@app.post("/api/control/resume")
async def control_resume():
    global PAUSED
    PAUSED = False
    return {"status": "resumed"}


@app.post("/api/control/stop")
async def control_stop():
    global STOPPED, PAUSED
    STOPPED, PAUSED = True, False
    return {"status": "stopped"}


@app.get("/")
async def root():
    return HTMLResponse(Path("templates/index.html").read_text())


def start_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")
