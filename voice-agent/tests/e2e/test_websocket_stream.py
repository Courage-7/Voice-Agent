"""End-to-end WebSocket connection and stream tests."""

import json
from starlette.testclient import TestClient
from app.auth.clerk import create_test_token
from app.main import app


def test_websocket_connection_lifecycle(fake_voice_provider):
    """Verify client WebSocket connection handshake and state events via /api/voice/ws."""
    client = TestClient(app)

    token = create_test_token(user_id="test_e2e_user", email="test_e2e@shinra.internal")
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Create session via REST first
    create_resp = client.post("/api/voice/sessions", json={"persona": "companion"}, headers=auth_headers)
    assert create_resp.status_code == 200
    session_id = create_resp.json()["session_id"]

    # 2. Browser-compatible authentication: token is a negotiated subprotocol,
    # never a query parameter where proxies and logs may retain it.
    with client.websocket_connect(
        f"/api/voice/ws/{session_id}", subprotocols=["shinra-auth", token]
    ) as websocket:
        # Receive initial state transition
        data = websocket.receive_text()
        msg = json.loads(data)
        assert msg == {"type": "SessionStateChange", "state": "connected"}
        assert websocket.receive_json() == {"type": "SessionStateChange", "state": "listening"}

        # Inject a text message
        websocket.send_text(json.dumps({
            "type": "InjectUserMessage",
            "message": "Hello Voice Agent",
        }))

        # Send a mock PCM audio frame
        mock_audio = bytes([0] * 1024)
        websocket.send_bytes(mock_audio)

    fake_voice_provider.connect.assert_awaited_once()
    fake_voice_provider.inject_user_message.assert_awaited_once_with("Hello Voice Agent")
    fake_voice_provider.send_audio.assert_awaited_once_with(mock_audio)
    fake_voice_provider.close.assert_awaited_once()


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
    assert "<!DOCTYPE html>" in resp.text


    resp_pg = client.get("/playground")
    assert resp_pg.status_code == 200
