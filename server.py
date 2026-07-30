"""FastAPI web server with auth, validation, and WebSocket broadcasting."""
import json
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import uvicorn
from pydantic import BaseModel, Field

import config

web_app = FastAPI(title="Golf Scraper API")
security = HTTPBasic(auto_error=False)
connections = []
PAUSED = False
STOPPED = False
IS_RUNNING = False

class ConfigData(BaseModel):
    SETTINGS: dict | None = None

class UpdateData(BaseModel):
    index: int = 0
    successes: int = 0
    failures: int = 0
    total_bonuses: int = 0
    new_bonuses: int = 0
    site_url: str = ""
    status_message: str = ""
    site_bonuses_gt_zero: int = 0
    N: int = 0
    elapsed: float = 0.0
    ip_score: int = 0
    site_new_bonuses: int = 0
    total_new_bonuses: int = 0
    nw: int = 1
    error_details: str = ""

def verify_auth(credentials: HTTPBasicCredentials | None = Depends(security)):
    """Optional auth — skip if no UI_PASS configured, else validate."""
    password = config.config_parser.get("SETTINGS", "ui_pass", fallback=None)
    if not password:
        return True  # no auth configured
    if not credentials:
        raise HTTPException(status_code=401, detail="Auth required")
    return credentials.username == config.UI_USER and credentials.password == password

@web_app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in connections:
            connections.remove(websocket)

@web_app.get("/api/config")
async def get_config(auth=Depends(verify_auth)):
    return config.load_config_dict()

@web_app.post("/api/config")
async def post_config(data: ConfigData, auth=Depends(verify_auth)):
    if data.SETTINGS:
        config.save_config_dict({"SETTINGS": data.SETTINGS})
    return {"status": "ok"}

@web_app.get("/api/status")
async def get_status():
    return {"paused": PAUSED, "stopped": STOPPED, "is_running": IS_RUNNING}

VALID_ACTIONS = {"pause", "resume", "stop"}

@web_app.post("/api/control/{action}")
async def control(action: str, auth=Depends(verify_auth)):
    global PAUSED, STOPPED
    if action not in VALID_ACTIONS:
        raise HTTPException(400, f"Invalid action: {action}. Use: pause, resume, stop")
        
    if action == "pause":
        PAUSED = True
    elif action == "resume":
        PAUSED = False
    elif action == "stop":
        STOPPED = True
        PAUSED = False
        
    status_map = {"pause": "paused", "resume": "resumed", "stop": "stopped"}
    return {"status": status_map[action]}

@web_app.post("/update")
async def update(data: UpdateData):
    for connection in connections:
        try:
            await connection.send_text(data.model_dump_json())
        except Exception:
            pass
    return {"status": "ok"}

@web_app.get("/")
async def root():
    return HTMLResponse(Path("templates/index.html").read_text())

def start_server():
    uvicorn.run(web_app, host="0.0.0.0", port=8000, log_level="error")
