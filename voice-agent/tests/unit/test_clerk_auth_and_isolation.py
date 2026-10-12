"""Clerk identity verification and authenticated ownership boundaries."""

from starlette.testclient import TestClient

from app.auth.clerk import clerk_verifier, create_test_token
from app.conversations.service import conversation_service
from app.main import app

client = TestClient(app)


def test_test_credentials_are_explicitly_limited_to_testing():
    token = create_test_token("user_test_99", "test@shinra.internal")
    user = clerk_verifier.verify_token(token)
    assert user is not None
    assert user.id == "user_test_99"
    assert user.email == "test@shinra.internal"
    assert clerk_verifier.verify_token("test.malformed") is None


def test_unauthenticated_requests_fail_on_protected_endpoints():
    for path, method, payload in (
        ("/api/conversations", "get", None),
        ("/api/memories", "get", None),
        ("/api/voice/sessions", "post", {"persona": "companion"}),
        ("/api/users/user_target", "get", None),
        ("/api/integrations/status", "get", None),
    ):
        response = getattr(client, method)(path, json=payload) if payload else getattr(client, method)(path)
        assert response.status_code == 401


async def test_cross_user_isolation_uses_verified_clerk_subjects():
    headers_a = {"Authorization": f"Bearer {create_test_token('user_alpha', 'alpha@shinra.internal')}"}
    headers_b = {"Authorization": f"Bearer {create_test_token('user_beta', 'beta@shinra.internal')}"}
    session_b_id = "session_beta_secret_42"

    await conversation_service.log_message(
        session_id=session_b_id,
        role="user",
        content="CONFIDENTIAL USER B DATA",
        user_id="user_beta",
    )

    list_res_a = client.get("/api/conversations", headers=headers_a)
    assert list_res_a.status_code == 200
    assert "CONFIDENTIAL USER B DATA" not in list_res_a.text

    assert client.get(f"/api/conversations/{session_b_id}", headers=headers_a).status_code == 403
    assert client.get(f"/api/conversations/{session_b_id}", headers=headers_b).status_code == 200


async def test_end_voice_session_rejects_unowned_active_session():
    from unittest.mock import AsyncMock, MagicMock
    from app.api.v1.voice import _active_sessions

    headers_a = {"Authorization": f"Bearer {create_test_token('user_alpha', 'alpha@shinra.internal')}"}
    headers_b = {"Authorization": f"Bearer {create_test_token('user_beta', 'beta@shinra.internal')}"}
    session_id = "session_active_alpha_123"

    mock_session = MagicMock()
    mock_session.user_id = "user_alpha"
    mock_session.close = AsyncMock()

    _active_sessions[session_id] = mock_session
    try:
        # User Beta attempts to end User Alpha's active session
        resp_b = client.post(f"/api/voice/sessions/{session_id}/end", headers=headers_b)
        assert resp_b.status_code == 403
        assert "Access denied" in resp_b.json()["detail"]
        assert session_id in _active_sessions
        mock_session.close.assert_not_called()

        # User Alpha successfully ends their own active session
        resp_a = client.post(f"/api/voice/sessions/{session_id}/end", headers=headers_a)
        assert resp_a.status_code == 200
        assert resp_a.json()["status"] == "ended"
        assert session_id not in _active_sessions
        mock_session.close.assert_called_once()
    finally:
        _active_sessions.pop(session_id, None)


def test_end_voice_session_rejects_missing_session():
    headers_a = {"Authorization": f"Bearer {create_test_token('user_alpha', 'alpha@shinra.internal')}"}
    resp = client.post("/api/voice/sessions/non_existent_session_999/end", headers=headers_a)
    assert resp.status_code == 404
