"""Unit tests for Phase 7: LangGraph Complex-Task Execution Engine."""

import asyncio
from unittest.mock import AsyncMock, patch
import pytest

from app.agent.complex_tasks.engine import complex_task_engine
from app.agent.complex_tasks.planner import complex_task_planner
from app.tools.registry import tool_registry
from app.tools.system.complex_task import RunComplexTaskTool


def test_complex_task_planner_decomposition():
    """Verify task planner decomposes high-level requests into ordered sub-steps."""
    # Pattern 1: Email + Doc
    steps = complex_task_planner.plan_steps("Search Q3 budget emails and draft note", {})
    assert len(steps) == 2
    assert steps[0]["tool_name"] == "search_emails"
    assert steps[1]["tool_name"] == "manage_google_doc"

    # Pattern 2: Web Research + Calendar
    steps2 = complex_task_planner.plan_steps("Research AI conferences and schedule meeting", {})
    assert len(steps2) == 2
    assert steps2[0]["tool_name"] == "perplexity_research"
    assert steps2[1]["tool_name"] == "list_calendar_events"


@pytest.mark.asyncio
async def test_complex_task_execution_flow():
    """Verify end-to-end multi-step task execution through ComplexTaskEngine."""
    with patch.object(tool_registry, "execute_tool", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"success": True, "data": "Step completed"}

        state = await complex_task_engine.start_task(
            goal="Search budget emails and create summary document",
            user_id="user_complex_1",
            session_id="sess_complex_1",
        )

        assert state["status"] == "completed"
        assert state["current_step_index"] == len(state["steps"])
        assert "completed your task" in state["spoken_summary"].lower()
        assert mock_exec.call_count == 2


@pytest.mark.asyncio
async def test_complex_task_confirmation_pause_and_resume():
    """Verify task pauses when encountering write confirmation and resumes upon user approval."""
    # Start task with email draft + send
    task_id = None
    step_calls = 0

    async def mock_execute(tool_name, arguments, **kwargs):
        nonlocal step_calls
        step_calls += 1
        if tool_name == "search_emails":
            return {"success": True, "emails": [{"id": "em_1", "subject": "Project X"}]}
        if tool_name == "send_email":
            if not arguments.get("confirmed"):
                return {
                    "success": False,
                    "requires_confirmation": True,
                    "message": "Please confirm sending email to the recipient.",
                }
            return {"success": True, "message_id": "msg_sent_123"}
        return {"success": True}

    with patch.object(tool_registry, "execute_tool", side_effect=mock_execute):
        # 1. Start task -> pauses on step 2 (send_email)
        state = await complex_task_engine.start_task(
            goal="Search email thread and send reply",
            user_id="user_pause_test",
        )
        task_id = state["task_id"]
        assert state["status"] == "awaiting_confirmation"
        assert "confirm" in state["confirmation_proposal"].lower()

        # 2. Resume task with confirmed=True
        resumed_state = await complex_task_engine.resume_task(
            task_id=task_id,
            confirmed=True,
        )
        assert resumed_state["status"] == "completed"
        assert resumed_state["current_step_index"] == 2


@pytest.mark.asyncio
async def test_complex_task_cancellation_on_declined_confirmation():
    """Verify task cancels cleanly if user rejects confirmation."""
    async def mock_execute(tool_name, arguments, **kwargs):
        if tool_name == "send_email" and not arguments.get("confirmed"):
            return {"success": False, "requires_confirmation": True, "message": "Confirm send?"}
        return {"success": True}

    with patch.object(tool_registry, "execute_tool", side_effect=mock_execute):
        state = await complex_task_engine.start_task(
            goal="Draft and send email",
            user_id="user_cancel_test",
        )
        assert state["status"] == "awaiting_confirmation"

        resumed_state = await complex_task_engine.resume_task(
            task_id=state["task_id"],
            confirmed=False,
        )
        assert resumed_state["status"] == "failed"
        assert "cancelled" in resumed_state["spoken_summary"].lower()


@pytest.mark.asyncio
async def test_run_complex_task_tool_integration():
    """Verify RunComplexTaskTool initiates complex task workflow."""
    tool = RunComplexTaskTool()
    with patch.object(complex_task_engine, "start_task", new_callable=AsyncMock) as mock_start:
        mock_start.return_value = {
            "status": "completed",
            "task_id": "task_123",
            "spoken_summary": "Task finished successfully.",
            "confirmation_proposal": None,
            "steps": [{"step_id": 1}],
            "collected_results": {},
        }

        result = await tool.execute(goal="Gather tech research")
        assert result["status"] == "completed"
        assert result["task_id"] == "task_123"
        assert mock_start.called
