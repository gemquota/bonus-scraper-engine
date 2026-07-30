"""
web_server.py - Dashboard Web Server

FastAPI server providing a real-time web dashboard via WebSocket.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import uvicorn

app = FastAPI()


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket."""
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """Broadcast a message to all connected clients."""
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.

    Clients connect here to receive live scraper progress updates.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/update")
async def update_data(data: dict):
    """
    Receive update from scraper and broadcast to all clients.

    Called by ui.update() to push real-time progress to the dashboard.
    """
    await manager.broadcast(json.dumps(data))
    return {"status": "ok"}


@app.get("/")
async def get():
    """Serve the React dashboard HTML."""
    with open("templates/index.html", "r") as f:
        return HTMLResponse(f.read())


def start_server():
    """Start the FastAPI server on port 8000."""
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")
