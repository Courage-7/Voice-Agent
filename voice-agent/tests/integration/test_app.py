"""Integration tests for central REST API endpoints with authentication."""

from starlette.testclient import TestClient
from app.auth.clerk import create_test_token
from app.main import app

client = TestClient(app)

TEST_USER_ID = "test_user"
test_token = create_test_token(user_id=TEST_USER_ID, email="test_user@shinra.internal")
auth_headers = {"Authorization": f"Bearer {test_token}"}


def test_health_endpoint():
    """Verify health endpoint under /api/health."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["tools_count"] == 18
    assert "readiness" in data


def test_api_tools_endpoint():
    """Verify tools schema endpoint under /api/tools."""
    response = client.get("/api/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert data["count"] == 18


def test_integrations_apps_endpoint():
    """Verify list of supported Composio apps."""
    response = client.get("/api/integrations/apps")
    assert response.status_code == 200
    data = response.json()
    assert "apps" in data
    assert len(data["apps"]) == 17
    assert "TAVILY" in [a["name"] for a in data["apps"]]


def test_integrations_connect_callback_scoped_tools(fake_composio):
    """Verify OAuth connection, callback, scoped tools, and disconnect."""
    # 1. Connect
    response = client.get("/api/integrations/connect/GMAIL", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["app"] == "GMAIL"
    assert "redirect_url" in data
    assert data["redirect_url"] == "https://oauth.example.invalid/test-gmail"
    assert fake_composio.connected_accounts.link.call_args.kwargs["user_id"] == TEST_USER_ID

    # 2. Callback
    cb_resp = client.get("/api/integrations/callback")
    assert cb_resp.status_code == 200
    assert "Account Connected Successfully" in cb_resp.text

    # 3. Scoped tools
    scoped_resp = client.get("/api/integrations/tools", headers=auth_headers)
    assert scoped_resp.status_code == 200
    scoped_data = scoped_resp.json()
    assert "tools" in scoped_data
    assert scoped_data["tools_count"] > 0

    # 4. Disconnect
    disc_resp = client.delete("/api/integrations/conn_test_gmail", headers=auth_headers)
    assert disc_resp.status_code == 200
    fake_composio.connected_accounts.delete.assert_called_once_with("conn_test_gmail")


def test_users_get_endpoint():
    """Verify user profile retrieval under /api/users for authenticated user."""
    user_token = create_test_token(user_id="user_123", email="user123@shinra.internal")
    u_headers = {"Authorization": f"Bearer {user_token}"}

    response = client.get("/api/users/user_123", headers=u_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "user_123"


def test_users_patch_endpoint():
    """Verify partial user update with PATCH semantics for authenticated user."""
    patch_token = create_test_token(user_id="patch_test_user", email="patch@shinra.internal")
    p_headers = {"Authorization": f"Bearer {patch_token}"}

    # Create user first via GET (auto-creates)
    client.get("/api/users/patch_test_user", headers=p_headers)

    # Patch only timezone
    patch_resp = client.patch(
        "/api/users/patch_test_user",
        json={"timezone": "America/New_York"},
        headers=p_headers,
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["timezone"] == "America/New_York"
    assert data["full_name"] == "User"


def test_memory_crud_lifecycle():
    """Verify full memory CRUD: create, read, update, delete for authenticated user."""
    crud_token = create_test_token(user_id="crud_user", email="crud@shinra.internal")
    c_headers = {"Authorization": f"Bearer {crud_token}"}

    # 1. Create
    save_resp = client.post(
        "/api/memories",
        json={
            "content": "User prefers morning meetings at 9 AM",
            "category": "preference",
        },
        headers=c_headers,
    )
    assert save_resp.status_code == 200
    memory = save_resp.json()["memory"]
    memory_id = memory["id"]

    # 2. Read
    get_resp = client.get("/api/memories?query=morning", headers=c_headers)
    assert get_resp.status_code == 200
    assert len(get_resp.json()["memories"]) > 0

    # 3. Update
    patch_resp = client.patch(
        f"/api/memories/{memory_id}",
        json={"content": "User prefers morning meetings at 10 AM"},
        headers=c_headers,
    )
    assert patch_resp.status_code == 200
    assert "10 AM" in patch_resp.json()["memory"]["content"]

    # 4. Delete
    del_resp = client.delete(f"/api/memories/{memory_id}", headers=c_headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # 5. Verify 404 on deleted
    del_again = client.delete(f"/api/memories/{memory_id}", headers=c_headers)
    assert del_again.status_code == 404


def test_conversations_list_and_delete():
    """Verify conversation listing, 401 unauthenticated check, and deletion."""
    # 1. Unauthenticated gets 401
    unauth_resp = client.get("/api/conversations")
    assert unauth_resp.status_code == 401

    # 2. Authenticated lists owned sessions
    list_resp = client.get("/api/conversations", headers=auth_headers)
    assert list_resp.status_code == 200
    assert "conversations" in list_resp.json()

    # 3. Non-existent returns 404
    get_resp = client.get("/api/conversations/nonexistent_session", headers=auth_headers)
    assert get_resp.status_code == 404


def test_voice_session_lifecycle():
    """Verify voice session creation and inspection via REST for authenticated user."""
    voice_token = create_test_token(user_id="voice_test_user", email="voice@shinra.internal")
    v_headers = {"Authorization": f"Bearer {voice_token}"}

    # 1. Create session
    create_resp = client.post(
        "/api/voice/sessions",
        json={"persona": "executive"},
        headers=v_headers,
    )
    assert create_resp.status_code == 200
    data = create_resp.json()
    session_id = data["session_id"]
    assert data["status"] == "created"
    assert data["user_id"] == "voice_test_user"

    # 2. Inspect session
    get_resp = client.get(f"/api/voice/sessions/{session_id}", headers=v_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["session_id"] == session_id

    # 3. End session (already inactive since no WS connected)
    end_resp = client.post(f"/api/voice/sessions/{session_id}/end", headers=v_headers)
    assert end_resp.status_code == 200


def test_playground_endpoint():
    """Verify playground serves HTML."""
    response = client.get("/playground")
    assert response.status_code == 200
    assert "SHINRA" in response.text or "Playground" in response.text
