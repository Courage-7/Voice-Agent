"""Unit tests for Phase 2: User Identity, Tool Semantics, Provider Resolution & Safety."""

import asyncio
from unittest.mock import AsyncMock, patch
import pytest

from app.tools.capability import capability_resolver
from app.tools.calendar.tools import CreateCalendarEventTool, ListCalendarEventsTool
from app.tools.email.tools import SearchEmailsTool, SendEmailTool
from app.tools.registry import tool_registry
from app.tools.workspace.dynamic_action import ExecuteAppActionTool
from app.tools.workspace.tools import GoogleDocsTool, GoogleDriveTool, GoogleSheetsTool


@pytest.mark.asyncio
async def test_email_provider_resolution_gmail_only():
    """Verify email resolver chooses Gmail when only Gmail is connected."""
    with patch.object(capability_resolver, "get_user_connected_apps", return_value=["GMAIL"]):
        provider, err = await capability_resolver.resolve_email_provider("user_1")
        assert provider == "gmail"
        assert err is None


@pytest.mark.asyncio
async def test_email_provider_resolution_outlook_only():
    """Verify email resolver chooses Outlook when only Outlook is connected."""
    with patch.object(capability_resolver, "get_user_connected_apps", return_value=["OUTLOOK"]):
        provider, err = await capability_resolver.resolve_email_provider("user_2")
        assert provider == "outlook"
        assert err is None


@pytest.mark.asyncio
async def test_email_provider_resolution_both_explicit():
    """Verify email resolver respects explicit user provider request when both are connected."""
    with patch.object(capability_resolver, "get_user_connected_apps", return_value=["GMAIL", "OUTLOOK"]):
        # Explicit Outlook
        provider, err = await capability_resolver.resolve_email_provider("user_3", requested_provider="outlook")
        assert provider == "outlook"
        assert err is None

        # Explicit Gmail
        provider, err = await capability_resolver.resolve_email_provider("user_3", requested_provider="gmail")
        assert provider == "gmail"
        assert err is None


@pytest.mark.asyncio
async def test_email_provider_resolution_both_ambiguous():
    """Verify email resolver returns disambiguation prompt when both are connected and neither specified."""
    with patch.object(capability_resolver, "get_user_connected_apps", return_value=["GMAIL", "OUTLOOK"]):
        provider, err = await capability_resolver.resolve_email_provider("user_4", requested_provider=None)
        assert provider is None
        assert err is not None
        assert err["requires_disambiguation"] is True
        assert "Gmail and Outlook" in err["spoken_summary"]


@pytest.mark.asyncio
async def test_calendar_provider_resolution_google_only():
    """Verify calendar resolver chooses Google Calendar when only Google is connected."""
    with patch.object(capability_resolver, "get_user_connected_apps", return_value=["GOOGLECALENDAR"]):
        provider, err = await capability_resolver.resolve_calendar_provider("user_5")
        assert provider == "google"
        assert err is None


@pytest.mark.asyncio
async def test_calendar_provider_resolution_both_ambiguous():
    """Verify calendar resolver returns disambiguation prompt when both Google and Outlook are connected."""
    with patch.object(capability_resolver, "get_user_connected_apps", return_value=["GOOGLECALENDAR", "OUTLOOK"]):
        provider, err = await capability_resolver.resolve_calendar_provider("user_6", requested_provider=None)
        assert provider is None
        assert err is not None
        assert err["requires_disambiguation"] is True
        assert "Google Calendar and Outlook" in err["spoken_summary"]


@pytest.mark.asyncio
async def test_dynamic_action_write_safety_boundary():
    """Verify ExecuteAppActionTool enforces confirmation on write operations even via dynamic routing."""
    tool = ExecuteAppActionTool()

    # 1. Unconfirmed write intent -> Halts for confirmation
    unconfirmed = await tool.execute(
        app_name="gmail",
        intent="send",
        parameters={"recipient": "bob@example.com", "subject": "Test"},
        confirmed=False,
    )
    assert unconfirmed["requires_confirmation"] is True
    assert "Would you like me to proceed?" in unconfirmed["spoken_summary"]

    # 2. Read intent -> Proceeds without confirmation
    with patch("app.integrations.composio.client.composio_gateway.execute_action", return_value={"success": True, "data": []}):
        read_res = await tool.execute(
            app_name="gmail",
            intent="fetch",
            parameters={"query": "invoice"},
            confirmed=False,
        )
        assert read_res["success"] is True


@pytest.mark.asyncio
async def test_workspace_tools_pass_entity_id():
    """Verify Google Sheets, Docs, and Drive tools propagate entity_id=user_id to Composio."""
    sheets_tool = GoogleSheetsTool()
    docs_tool = GoogleDocsTool()
    drive_tool = GoogleDriveTool()

    with patch("app.integrations.composio.client.composio_gateway.execute_action", return_value={"success": True}) as mock_exec:
        await sheets_tool.execute(spreadsheet_id="sheet_123", action="read", user_id="user_alice")
        assert mock_exec.call_args.kwargs.get("entity_id") == "user_alice"

        await docs_tool.execute(content="Hello world", title="Doc 1", user_id="user_bob")
        assert mock_exec.call_args.kwargs.get("entity_id") == "user_bob"

        await drive_tool.execute(query="roadmap", user_id="user_charlie")
        assert mock_exec.call_args.kwargs.get("entity_id") == "user_charlie"


def test_deepgram_schemas_exclude_meta_tools():
    """Verify tool_registry.get_deepgram_function_schemas() excludes execute_app_action by default."""
    schemas = tool_registry.get_deepgram_function_schemas()
    schema_names = [s["name"] for s in schemas]

    assert "send_email" in schema_names
    assert "search_emails" in schema_names
    assert "create_calendar_event" in schema_names
    assert "list_calendar_events" in schema_names
    assert "execute_app_action" not in schema_names  # Excluded to avoid competing schemas


@pytest.mark.asyncio
async def test_search_emails_preserves_identifiers():
    """Verify SearchEmailsTool preserves message_id and thread_id for multi-step workflows."""
    tool = SearchEmailsTool()

    mock_response = {
        "success": True,
        "data": {
            "messages": [
                {
                    "id": "msg_9988",
                    "threadId": "thread_4455",
                    "sender": "sarah@company.com",
                    "subject": "Q3 Planning",
                    "date": "2026-08-24T12:00:00Z",
                    "snippet": "Here are the notes for Q3...",
                }
            ]
        },
    }

    with patch("app.integrations.composio.client.composio_gateway.execute_action", return_value=mock_response):
        res = await tool.execute(query="Q3 Planning", user_id="user_test")
        assert res["success"] is True
        assert len(res["emails"]) == 1
        email_item = res["emails"][0]
        assert email_item["message_id"] == "msg_9988"
        assert email_item["thread_id"] == "thread_4455"
        assert email_item["sender"] == "sarah@company.com"
        assert email_item["subject"] == "Q3 Planning"
