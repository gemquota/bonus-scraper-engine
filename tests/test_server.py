"""Tests for server.py — FastAPI endpoints (with auth where required)."""
from fastapi.testclient import TestClient
import server

client = TestClient(server.web_app)
AUTH = ("admin", "password")  # from in/config/config.ini

class TestRoot:
    def test_root_returns_html(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

class TestStatus:
    def test_status_returns_flags(self):
        r = client.get("/api/status")
        assert r.status_code == 200
        data = r.json()
        assert "paused" in data
        assert "stopped" in data
        assert "is_running" in data

class TestConfig:
    def test_get_config_requires_auth(self):
        r = client.get("/api/config")
        assert r.status_code == 401

    def test_get_config_with_auth(self):
        r = client.get("/api/config", auth=AUTH)
        assert r.status_code == 200
        assert isinstance(r.json(), dict)

    def test_post_config_with_auth(self):
        r = client.post("/api/config", json={"SETTINGS": {"min_delay": "2.0"}}, auth=AUTH)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

class TestControl:
    def test_pause_requires_auth(self):
        r = client.post("/api/control/pause")
        assert r.status_code == 401

    def test_pause_with_auth(self):
        r = client.post("/api/control/pause", auth=AUTH)
        assert r.json()["status"] == "paused"
        assert server.PAUSED is True

    def test_resume(self):
        client.post("/api/control/pause", auth=AUTH)
        r = client.post("/api/control/resume", auth=AUTH)
        assert r.json()["status"] == "resumed"
        assert server.PAUSED is False

    def test_stop(self):
        r = client.post("/api/control/stop", auth=AUTH)
        assert r.json()["status"] == "stopped"
        assert server.STOPPED is True

    def test_invalid_action(self):
        r = client.post("/api/control/bogus", auth=AUTH)
        assert r.status_code == 400

class TestUpdate:
    def test_update_broadcasts(self):
        r = client.post("/update", json={"index": 5, "status_message": "test"})
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

class TestWebSocket:
    def test_ws_connect_and_ping(self):
        with client.websocket_connect("/ws") as ws:
            ws.send_text("ping")
            resp = ws.receive_text()
            assert resp == "pong"
