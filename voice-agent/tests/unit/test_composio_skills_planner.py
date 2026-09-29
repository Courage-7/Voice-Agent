"""Unit tests for Composio tool-level skills resolution and unified complex task planning."""

import asyncio
from unittest.mock import AsyncMock, patch
import pytest

from app.agent.complex_tasks.engine import complex_task_engine
from app.agent.complex_tasks.planner import complex_task_planner
from app.integrations.composio.client import composio_gateway
from app.tools.registry import tool_registry


@pytest.mark.asyncio
async def test_composio_skill_research_and_doc_resolution():
    """Verify research + document goal dynamically resolves to Perplexity/SerpApi and Google Docs."""
    with patch.object(
        composio_gateway,
        "get_connected_accounts",
        new_callable=AsyncMock,
        return_value=[{"app": "PERPLEXITYAI", "status": "ACTIVE"}, {"app": "GOOGLEDOCS", "status": "ACTIVE"}],
    ):
        steps = await complex_task_planner.plan_steps(
            goal="Research latest AI agent developments and save notes in a document",
            user_id="user_skill_1",
        )
        assert len(steps) == 2
        assert steps[0]["tool_name"] == "perplexity_ai_research"
        assert steps[1]["tool_name"] == "manage_google_doc"


@pytest.mark.asyncio
async def test_composio_skill_email_sheet_logging_resolution():
    """Verify email + sheet logging goal dynamically resolves to search_emails and manage_google_sheet."""
    with patch.object(
        composio_gateway,
        "get_connected_accounts",
        new_callable=AsyncMock,
        return_value=[{"app": "GMAIL", "status": "ACTIVE"}, {"app": "GOOGLESHEETS", "status": "ACTIVE"}],
    ):
        steps = await complex_task_planner.plan_steps(
            goal="Search recent emails and log results into spreadsheet",
            user_id="user_skill_2",
        )
        assert len(steps) == 2
        assert steps[0]["tool_name"] == "search_emails"
        assert steps[1]["tool_name"] == "manage_google_sheet"


@pytest.mark.asyncio
async def test_composio_skill_calendar_availability_and_booking():
    """Verify calendar check and schedule resolves to list_calendar_events and create_calendar_event."""
    with patch.object(
        composio_gateway,
        "get_connected_accounts",
        new_callable=AsyncMock,
        return_value=[{"app": "GOOGLECALENDAR", "status": "ACTIVE"}],
    ):
        steps = await complex_task_planner.plan_steps(
            goal="Check calendar slots and schedule team sync",
            user_id="user_skill_3",
        )
        assert len(steps) == 2
        assert steps[0]["tool_name"] == "list_calendar_events"
        assert steps[1]["tool_name"] == "create_calendar_event"


@pytest.mark.asyncio
async def test_composio_skill_fallback_to_heuristics():
    """Verify fallback when dynamic Composio skill returns no matches or errors."""
    with patch.object(composio_gateway, "resolve_skill_steps", new_callable=AsyncMock, return_value=[]):
        steps = await complex_task_planner.plan_steps(
            goal="Search Q3 budget emails and draft note",
            user_id="user_fallback",
        )
        assert len(steps) == 2
        assert steps[0]["tool_name"] == "search_emails"
        assert steps[1]["tool_name"] == "manage_google_doc"


@pytest.mark.asyncio
async def test_engine_single_execution_gateway_with_confirmation():
    """Verify ComplexTaskEngine routes all steps through tool_registry without redundant confirmation logic."""
    step_calls = []

    async def mock_execute(tool_name, arguments, **kwargs):
        step_calls.append((tool_name, arguments))
        if tool_name == "manage_google_doc":
            if not arguments.get("confirmed"):
                return {
                    "status": "confirmation_required",
                    "requires_confirmation": True,
                    "message": "Please confirm creating this document.",
                }
            return {"status": "success", "doc_id": "doc_abc123"}
        return {"status": "success", "data": "emails_found"}

    with patch.object(
        composio_gateway,
        "get_connected_accounts",
        new_callable=AsyncMock,
        return_value=[{"app": "PERPLEXITYAI", "status": "ACTIVE"}, {"app": "GOOGLEDOCS", "status": "ACTIVE"}],
    ):
        with patch.object(tool_registry, "execute_tool", side_effect=mock_execute):
            # 1. Start task -> pauses on manage_google_doc for confirmation
            state = await complex_task_engine.start_task(
                goal="Research AI and save in doc",
                user_id="user_ssot_test",
            )
            assert state["status"] == "awaiting_confirmation"
            assert "confirm" in state["confirmation_proposal"].lower()
            assert len(step_calls) == 2

            # 2. Resuming with confirmation proceeds through tool_registry
            resumed = await complex_task_engine.resume_task(
                task_id=state["task_id"],
                confirmed=True,
            )
            assert resumed["status"] == "completed"
            assert len(step_calls) == 3


@pytest.mark.asyncio
async def test_composio_skill_notion_notes_resolution():
    """Verify research + Notion notes goal resolves to search + execute_app_action(notion, create)."""
    with patch.object(
        composio_gateway,
        "get_connected_accounts",
        new_callable=AsyncMock,
        return_value=[{"app": "NOTION", "status": "ACTIVE"}],
    ):
        steps = await complex_task_planner.plan_steps(
            goal="Research quantum computing and save notes into Notion",
            user_id="user_notion_1",
        )
        assert len(steps) == 2
        assert steps[0]["tool_name"] == "web_search_serpapi"
        assert steps[1]["tool_name"] == "execute_app_action"
        assert steps[1]["arguments"]["app_name"] == "notion"
        assert steps[1]["arguments"]["intent"] == "create"


@pytest.mark.asyncio
async def test_composio_skill_teams_messaging_resolution():
    """Verify team notification goal resolves to execute_app_action(microsoft_teams, send)."""
    with patch.object(
        composio_gateway,
        "get_connected_accounts",
        new_callable=AsyncMock,
        return_value=[{"app": "MICROSOFT_TEAMS", "status": "ACTIVE"}],
    ):
        steps = await complex_task_planner.plan_steps(
            goal="Send a message on Teams to notify the team about sprint release",
            user_id="user_teams_1",
        )
        assert len(steps) == 1
        assert steps[0]["tool_name"] == "execute_app_action"
        assert steps[0]["arguments"]["app_name"] == "microsoft_teams"
        assert steps[0]["arguments"]["intent"] == "send"


@pytest.mark.asyncio
async def test_composio_skill_drive_search_resolution():
    """Verify Google Drive search goal resolves to search_google_drive."""
    with patch.object(
        composio_gateway,
        "get_connected_accounts",
        new_callable=AsyncMock,
        return_value=[{"app": "GOOGLEDRIVE", "status": "ACTIVE"}],
    ):
        steps = await complex_task_planner.plan_steps(
            goal="Search Google Drive for quarterly earnings document",
            user_id="user_drive_1",
        )
        assert len(steps) == 1
        assert steps[0]["tool_name"] == "search_google_drive"


def test_dynamic_app_hydration_in_deepgram_schemas():
    """Verify execute_app_action is included only when dynamic-only apps are connected."""
    # When only standard Google apps are connected, execute_app_action is excluded to avoid competition
    schemas_standard = tool_registry.get_deepgram_function_schemas(
        connected_apps=["GMAIL", "GOOGLECALENDAR"]
    )
    names_standard = {s["name"] for s in schemas_standard}
    assert "execute_app_action" not in names_standard
    assert "search_emails" in names_standard
    assert "list_calendar_events" in names_standard

    # When a dynamic-only app like Notion is connected, execute_app_action is automatically hydrated
    schemas_notion = tool_registry.get_deepgram_function_schemas(
        connected_apps=["NOTION"]
    )
    names_notion = {s["name"] for s in schemas_notion}
    assert "execute_app_action" in names_notion

