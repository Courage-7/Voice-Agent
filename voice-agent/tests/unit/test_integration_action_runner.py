"""Regression coverage for connection-gated Gmail and Calendar execution."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agent.integration_actions import (
    execute_requested_integration_actions,
    format_integration_response,
    plan_integration_actions,
)
from app.agent.task_execution import CapabilityTask, CapabilityExecutionEngine, TaskState
from app.tools.capability import capability_resolver


def test_planner_extracts_each_requested_integration_action():
    actions = plan_integration_actions(
        "Retrieve my recent Gmail messages and upcoming Google Calendar events"
    )

    assert [action.tool_name for action in actions] == ["search_emails", "list_calendar_events"]
    assert actions[0].arguments["provider"] == "gmail"
    assert actions[1].arguments["provider"] == "google"


@pytest.mark.asyncio
async def test_connected_apps_are_a_precondition_not_a_terminal_result():
    accounts = [
        {"app": "GMAIL", "status": "ACTIVE", "is_active": True, "connection_id": "gmail-1"},
        {"app": "GOOGLE_CALENDAR", "status": "CONNECTED", "is_active": True, "connection_id": "cal-1"},
    ]
    tool_results = [
        {
            "success": True,
            "spoken_summary": "Found 1 email.",
            "emails": [{"sender": "Ada", "subject": "Project update"}],
        },
        {
            "success": True,
            "spoken_summary": "Found 1 upcoming event.",
            "events": [{"title": "Planning", "start": "2026-09-21T09:00:00Z"}],
        },
    ]
    activity = []

    async def record(event):
        activity.append(event)

    with patch(
        "app.agent.task_execution.composio_gateway.get_connected_accounts",
        new=AsyncMock(return_value=accounts),
    ), patch(
        "app.agent.task_execution.tool_registry.execute_tool",
        new=AsyncMock(side_effect=tool_results),
    ) as execute_tool:
        execution = await execute_requested_integration_actions(
            "Retrieve my recent Gmail messages and upcoming Google Calendar events",
            user_id="authenticated-user",
            session_id="session-1",
            on_activity=record,
        )

    assert execution is not None
    assert [result["tool_name"] for result in execution["results"]] == ["search_emails", "list_calendar_events"]
    assert execute_tool.await_count == 2
    assert [call.kwargs["user_id"] for call in execute_tool.await_args_list] == ["authenticated-user", "authenticated-user"]
    assert [event["type"] for event in activity].count("FunctionCallRequest") == 2
    assert [event["type"] for event in activity].count("FunctionCallResult") == 2
    response = format_integration_response(execution)
    assert "Project update" in response
    assert "Planning" in response


@pytest.mark.asyncio
async def test_explicit_provider_must_belong_to_authenticated_user():
    with patch.object(capability_resolver, "get_user_connected_apps", return_value=["OUTLOOK"]):
        provider, error = await capability_resolver.resolve_email_provider("user-1", requested_provider="gmail")

    assert provider is None
    assert error["status"] == "connection_unavailable"


@pytest.mark.asyncio
async def test_task_engine_requires_validated_result_before_completion():
    task = CapabilityTask(
        goal="retrieve records",
        tool_name="search_emails",
        capability="email",
        allows_empty=False,
    )
    engine = CapabilityExecutionEngine()

    with patch(
        "app.agent.task_execution.composio_gateway.get_connected_accounts",
        new=AsyncMock(return_value=[{"app": "GMAIL", "status": "ACTIVE", "is_active": True}]),
    ), patch.object(engine.registry, "execute_tool", new=AsyncMock(return_value={"success": True, "count": 0, "emails": []})):
        summary = await engine.execute([task], user_id="user-1", session_id="session-1")

    assert summary.complete is False
    assert task.state == TaskState.FAILED
    assert task.failure_code == "incomplete_result"
