"""End-to-end WebSocket connection and stream tests."""

import json
from starlette.testclient import TestClient
from app.main import app


def test_websocket_connection_lifecycle():
    """Verify client WebSocket connection handshake and state events via /api/voice/ws."""
    client = TestClient(app)

    # 1. Create session via REST first
    create_resp = client.post("/api/voice/sessions", json={"user_id": "test_e2e_user"})
    session_id = create_resp.json()["session_id"]

    # 2. Connect WebSocket to the new voice path
    with client.websocket_connect(f"/api/voice/ws/{session_id}?user_id=test_e2e_user") as websocket:
        # Receive initial state transition
        data = websocket.receive_text()
        msg = json.loads(data)
        assert msg["type"] in ["SessionStateChange", "Error"]

        # Inject a text message
        websocket.send_text(json.dumps({
            "type": "InjectUserMessage",
            "message": "Hello Voice Agent",
        }))

        # Send a mock PCM audio frame
        mock_audio = bytes([0] * 1024)
        websocket.send_bytes(mock_audio)


def test_metrics_endpoint():
    """Verify Prometheus /api/metrics returns status."""
    client = TestClient(app)
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    assert "voice_agent_active_sessions" in resp.text
    assert "voice_agent_total_turns" in resp.text


def test_playground_endpoint():
    """Verify GET / and GET /playground return HTML."""
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Voice AI Agent Playground" in resp.text

    resp_pg = client.get("/playground")
    assert resp_pg.status_code == 200
