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
