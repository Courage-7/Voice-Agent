"""Integration tests for central REST API endpoints."""

from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify health endpoint under /api/health."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["tools_count"] == 15


def test_api_tools_endpoint():
    """Verify tools schema endpoint under /api/tools."""
    response = client.get("/api/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert data["count"] == 15


def test_integrations_apps_endpoint():
    """Verify list of supported Composio apps."""
    response = client.get("/api/integrations/apps")
    assert response.status_code == 200
    data = response.json()
    assert "apps" in data
    assert len(data["apps"]) == 8


def test_integrations_connect_callback_scoped_tools():
    """Verify OAuth connection, callback, scoped tools, and disconnect."""
    # 1. Connect
    response = client.get("/api/integrations/connect/GMAIL?user_id=test_user")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["app"] == "GMAIL"
    assert "redirect_url" in data

    # 2. Callback
    cb_resp = client.get("/api/integrations/callback")
    assert cb_resp.status_code == 200
    assert "Account Connected Successfully" in cb_resp.text

    # 3. Scoped tools (renamed from /connected-tools to /tools)
    scoped_resp = client.get("/api/integrations/tools?user_id=test_user")
    assert scoped_resp.status_code == 200
    scoped_data = scoped_resp.json()
    assert "tools" in scoped_data
    assert scoped_data["tools_count"] > 0

    # 4. Disconnect
    disc_resp = client.delete("/api/integrations/conn_mock_123")
    assert disc_resp.status_code == 200


def test_users_get_endpoint():
    """Verify user profile retrieval under /api/users."""
    response = client.get("/api/users/user_123")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "user_123"


def test_users_patch_endpoint():
    """Verify partial user update with PATCH semantics."""
    # Create user first via GET (auto-creates)
    client.get("/api/users/patch_test_user")

    # Patch only timezone
    patch_resp = client.patch("/api/users/patch_test_user", json={
        "timezone": "America/New_York",
    })
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["timezone"] == "America/New_York"
    # full_name should remain the default "User", not be wiped
    assert data["full_name"] == "User"


def test_memory_crud_lifecycle():
    """Verify full memory CRUD: create, read, update, delete."""
    # 1. Create
    save_resp = client.post("/api/memories", json={
        "user_id": "crud_user",
        "content": "User prefers morning meetings at 9 AM",
        "category": "preference",
    })
    assert save_resp.status_code == 200
    memory = save_resp.json()["memory"]
    memory_id = memory["id"]

    # 2. Read
    get_resp = client.get("/api/memories?user_id=crud_user&query=morning")
    assert get_resp.status_code == 200
    assert len(get_resp.json()["memories"]) > 0

    # 3. Update
    patch_resp = client.patch(f"/api/memories/{memory_id}", json={
        "content": "User prefers morning meetings at 10 AM",
    })
    assert patch_resp.status_code == 200
    assert "10 AM" in patch_resp.json()["memory"]["content"]

    # 4. Delete
    del_resp = client.delete(f"/api/memories/{memory_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # 5. Verify 404 on deleted
    del_again = client.delete(f"/api/memories/{memory_id}")
    assert del_again.status_code == 404


def test_conversations_list_and_delete():
    """Verify conversation listing and deletion."""
    # List (empty initially for this test)
    list_resp = client.get("/api/conversations")
    assert list_resp.status_code == 200
    assert "conversations" in list_resp.json()

    # Get non-existent returns 404
    get_resp = client.get("/api/conversations/nonexistent_session")
    assert get_resp.status_code == 404


def test_voice_session_lifecycle():
    """Verify voice session creation and inspection via REST."""
    # 1. Create session
    create_resp = client.post("/api/voice/sessions", json={
        "user_id": "voice_test_user",
        "persona": "executive",
    })
    assert create_resp.status_code == 200
    data = create_resp.json()
    session_id = data["session_id"]
    assert data["status"] == "created"
    assert data["user_id"] == "voice_test_user"

    # 2. Inspect session
    get_resp = client.get(f"/api/voice/sessions/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["session_id"] == session_id

    # 3. End session (already inactive since no WS connected)
    end_resp = client.post(f"/api/voice/sessions/{session_id}/end")
    assert end_resp.status_code == 200


def test_playground_endpoint():
    """Verify playground serves HTML."""
    response = client.get("/playground")
    assert response.status_code == 200
    assert "Voice AI Agent Playground" in response.text
