"""Comprehensive tests for Composio project apps discovery, official logos, and auth wiring."""

import pytest
from types import SimpleNamespace
from app.integrations.composio.client import ComposioGateway, composio_gateway
from app.tools.workspace.dynamic_action import ExecuteAppActionTool
from app.api.v1.integrations import get_connection_status, get_user_scoped_tools
from app.auth.models import AuthUser
from unittest.mock import AsyncMock, MagicMock, patch


def test_installed_sdk_supports_the_gateway_contract():
    """Catch namespace collisions that mocked SDK tests cannot detect."""
    from importlib.metadata import PackageNotFoundError, version
    from composio import Composio

    with pytest.raises(PackageNotFoundError):
        version("composio-core")
    client = Composio(api_key="offline-contract-check")
    assert callable(client.auth_configs.list)
    assert callable(client.connected_accounts.link)
    assert callable(client.connected_accounts.list)
    assert callable(client.tools.execute)


@pytest.mark.asyncio
@pytest.mark.parametrize("toolkit,scheme", [("gmail", "OAUTH2"), ("tavily", "API_KEY")])
async def test_connect_resolves_enabled_config_on_later_page(toolkit, scheme):
    gateway = ComposioGateway(api_key="")
    client = MagicMock()
    # Dict pages and SDK models are both supported; disabled configs must be skipped.
    client.auth_configs.list.side_effect = [
        {"items": [{"id": "disabled", "status": "DISABLED", "toolkit": {"slug": toolkit}}], "next_cursor": "page2"},
        SimpleNamespace(items=[SimpleNamespace(
            id="ac_enabled", status="ENABLED", toolkit=SimpleNamespace(slug=toolkit), auth_scheme=scheme,
        )], next_cursor=None),
    ]
    client.connected_accounts.link.return_value = {
        "redirect_url": "https://connect.composio.dev/link/test", "connected_account_id": "ca_test",
    }
    gateway._client = client
    result = await gateway.initiate_connection(toolkit.upper(), entity_id="signed-in-user")
    assert result["success"] is True
    client.auth_configs.list.assert_any_call(limit=100, show_disabled=False, cursor="page2")
    client.connected_accounts.link.assert_called_once_with(user_id="signed-in-user", auth_config_id="ac_enabled")


@pytest.mark.asyncio
async def test_failed_lookup_is_not_reported_as_missing_config():
    gateway = ComposioGateway(api_key="")
    client = MagicMock()
    client.auth_configs.list.side_effect = RuntimeError("upstream private details")
    gateway._client = client
    result = await gateway.initiate_connection("GMAIL", entity_id="user")
    assert result["success"] is False
    assert "Could not retrieve" in result["error"]
    assert "No active auth config" not in result["error"]
    assert "private details" not in result["error"]
    client.connected_accounts.link.assert_not_called()
    with pytest.raises(RuntimeError, match="Could not retrieve"):
        gateway.get_supported_apps()


def test_empty_live_project_does_not_show_fallback_connectors():
    gateway = ComposioGateway(api_key="")
    gateway._client = SimpleNamespace(auth_configs=SimpleNamespace(list=MagicMock(return_value={"items": []})))
    assert gateway.get_supported_apps() == []


@pytest.mark.asyncio
async def test_disabled_config_is_not_reused_from_cache():
    gateway = ComposioGateway(api_key="")
    gateway._auth_configs_cache["gmail"] = "old_config"
    client = MagicMock()
    client.auth_configs.list.return_value = {"items": [{"id": "old_config", "status": "DISABLED", "toolkit": {"slug": "gmail"}}]}
    gateway._client = client
    result = await gateway.initiate_connection("GMAIL", entity_id="user")
    assert result["success"] is False
    assert "No active auth config" in result["error"]
    client.connected_accounts.link.assert_not_called()


@pytest.mark.asyncio
async def test_missing_connect_url_does_not_report_success():
    gateway = ComposioGateway(api_key="")
    client = MagicMock()
    client.auth_configs.list.return_value = {"items": [{"id": "ac_gmail", "toolkit": {"slug": "gmail"}}]}
    client.connected_accounts.link.return_value = {"connected_account_id": "ca_test"}
    gateway._client = client
    result = await gateway.initiate_connection("GMAIL", entity_id="user")
    assert result["success"] is False
    assert "valid authorization link" in result["error"]


def test_baseline_project_apps_structure():
    """Verify that fallback baseline apps strictly match enabled project apps and have official logos."""
    apps = composio_gateway.get_supported_apps()
    assert isinstance(apps, list)
    assert len(apps) >= 16

    app_names = {a["name"].lower() for a in apps}
    # Must contain newly enabled project apps
    assert "microsoft_teams" in app_names
    assert "whatsapp" in app_names
    assert "telegram" in app_names
    assert "linkedin" in app_names
    assert "neon" in app_names
    assert "tavily" in app_names
    assert "i_love_pdf" in app_names
    assert "notion" in app_names

    # Must NOT contain unconfigured apps
    assert "github" not in app_names
    assert "linear" not in app_names
    assert "stripe" not in app_names
    assert "postgresql" not in app_names

    # Verify official CDN logo URL format for all apps
    for app in apps:
        assert "logo_url" in app
        assert app["logo_url"].startswith("https://logos.composio.dev/api/")
        assert "capability" in app
        assert "categories" in app
        assert "display_name" in app


@pytest.mark.asyncio
async def test_initiate_connection_returns_both_redirect_and_auth_urls():
    """Verify initiate_connection provides both redirect_url and auth_url for popup compatibility."""
    gateway = ComposioGateway(api_key="")

    mock_client = MagicMock()
    mock_link_resp = SimpleNamespace(
        redirect_url="https://connect.composio.dev/link/link_test123",
        connected_account_id="conn_123",
    )

    mock_client.connected_accounts.link = MagicMock(return_value=mock_link_resp)
    mock_client.auth_configs.list = MagicMock(return_value=SimpleNamespace(items=[
        SimpleNamespace(toolkit=SimpleNamespace(slug="microsoft_teams"), id="ac_test123")
    ]))
    gateway._client = mock_client

    result = await gateway.initiate_connection("microsoft_teams", entity_id="user_abc")
    assert result["success"] is True
    assert result["redirect_url"] == "https://connect.composio.dev/link/link_test123"
    assert result["auth_url"] == "https://connect.composio.dev/link/link_test123"
    assert result["entity_id"] == "user_abc"
    assert result["connection_id"] == "conn_123"
    mock_client.connected_accounts.link.assert_called_once_with(
        user_id="user_abc", auth_config_id="ac_test123",
    )


@pytest.mark.asyncio
async def test_get_connected_accounts_normalizes_slugs():
    """Verify get_connected_accounts returns uppercase app and app_key."""
    gateway = ComposioGateway(api_key="test-key")
    mock_client = MagicMock()

    mock_acc1 = MagicMock()
    mock_acc1.toolkit.slug = "microsoft_teams"
    mock_acc1.status = "ACTIVE"
    mock_acc1.id = "ca_1"

    mock_acc2 = MagicMock()
    mock_acc2.toolkit = None
    mock_acc2.toolkit_slug = "whatsapp"
    mock_acc2.status = "ACTIVE"
    mock_acc2.id = "ca_2"

    mock_res = MagicMock()
    mock_res.items = [mock_acc1, mock_acc2]
    mock_client.connected_accounts.list = MagicMock(return_value=mock_res)
    gateway._client = mock_client

    accounts = await gateway.get_connected_accounts(entity_id="user_abc")
    assert len(accounts) == 2
    assert accounts[0]["app"] == "MICROSOFT_TEAMS"
    assert accounts[0]["app_key"] == "MICROSOFT_TEAMS"
    assert accounts[1]["app"] == "WHATSAPP"
    assert accounts[1]["app_key"] == "WHATSAPP"


@pytest.mark.asyncio
async def test_connection_state_cache_is_invalidated_for_oauth_changes():
    """A newly linked or removed account must not be hidden by the 60s cache."""
    gateway = ComposioGateway(api_key="")
    gateway._connected_accounts_cache["user_abc"] = (0.0, [{"app": "GMAIL"}])

    gateway.invalidate_connected_accounts("user_abc")

    assert "user_abc" not in gateway._connected_accounts_cache


@pytest.mark.asyncio
async def test_connection_status_bypasses_cached_provider_state():
    """The OAuth polling endpoint must read a completed connection immediately."""
    user = AuthUser(id="user_abc", email="test@example.com", is_active=True)
    with patch(
        "app.api.v1.integrations.composio_gateway.get_connected_accounts",
        new_callable=AsyncMock,
    ) as get_accounts:
        get_accounts.return_value = []

        await get_connection_status(current_user=user)

    get_accounts.assert_awaited_once_with(entity_id="user_abc", force_refresh=True)


def test_dynamic_action_tool_supports_new_apps():
    """Verify ExecuteAppActionTool recognizes newly enabled apps and their action slugs."""
    tool = ExecuteAppActionTool()
    allowed_apps = tool.parameters["properties"]["app_name"]["enum"]

    for expected in ["microsoft_teams", "whatsapp", "telegram", "linkedin", "neon", "notion", "i_love_pdf"]:
        assert expected in allowed_apps

    # Check slug resolution
    assert tool._resolve_slug("microsoft_teams", "send") == "MICROSOFT_TEAMS_SEND_CHAT_MESSAGE"
    assert tool._resolve_slug("whatsapp", "send") == "WHATSAPP_SEND_MESSAGE"
    assert tool._resolve_slug("telegram", "send") == "TELEGRAM_SEND_MESSAGE"
    assert tool._resolve_slug("linkedin", "post") == "LINKEDIN_CREATE_POST"
    assert tool._resolve_slug("neon", "list") == "NEON_LIST_PROJECTS"
    assert tool._resolve_slug("notion", "create") == "NOTION_CREATE_NOTION_PAGE"
    assert tool._resolve_slug("i_love_pdf", "process") == "I_LOVE_PDF_PROCESS_PDF"


@pytest.mark.asyncio
async def test_user_scoped_tools_includes_workspace_for_new_apps():
    """Verify get_user_scoped_tools activates workspace capability for newly connected project apps."""
    fake_user = AuthUser(id="user_test", email="test@example.com", is_active=True)

    with patch("app.api.v1.integrations.composio_gateway.get_connected_accounts", new_callable=AsyncMock) as mock_conn:
        mock_conn.return_value = [
            {"app": "MICROSOFT_TEAMS", "status": "ACTIVE"},
            {"app": "NEON", "status": "ACTIVE"},
        ]

        result = await get_user_scoped_tools(current_user=fake_user)
        assert "workspace" in result["active_capabilities"]
        assert "system" in result["active_capabilities"]
        assert "memory" in result["active_capabilities"]
