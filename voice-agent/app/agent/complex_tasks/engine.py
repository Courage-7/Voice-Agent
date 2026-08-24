"""Complex Task Execution Engine with pause/resume and safety confirmation."""

import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from app.agent.complex_tasks.planner import complex_task_planner
from app.agent.complex_tasks.state import ComplexTaskState, TaskStep
from app.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class ComplexTaskEngine:
    """Orchestrates multi-step workflows using LangGraph patterns with unified safety boundaries."""

    def __init__(self) -> None:
        self._active_tasks: Dict[str, ComplexTaskState] = {}

    def get_task(self, task_id: str) -> Optional[ComplexTaskState]:
        """Retrieve task state by task ID."""
        return self._active_tasks.get(task_id)

    async def start_task(
        self,
        goal: str,
        user_id: str = "default_user",
        session_id: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> ComplexTaskState:
        """Initialize and execute a new complex multi-step task."""
        task_id = f"task_{uuid4().hex[:8]}"
        steps = complex_task_planner.plan_steps(goal=goal, context=context or {})

        state: ComplexTaskState = {
            "task_id": task_id,
            "user_id": user_id,
            "session_id": session_id,
            "goal": goal,
            "steps": steps,
            "current_step_index": 0,
            "collected_results": {},
            "status": "executing",
            "clarification_question": None,
            "confirmation_proposal": None,
            "spoken_summary": None,
            "error": None,
        }
        self._active_tasks[task_id] = state

        return await self._run_execution_loop(state)

    async def resume_task(
        self,
        task_id: str,
        user_input: Optional[str] = None,
        confirmed: bool = False,
    ) -> ComplexTaskState:
        """Resume a paused complex task after user confirmation or clarification."""
        state = self.get_task(task_id)
        if not state:
            raise ValueError(f"Complex task '{task_id}' not found.")

        if state["status"] == "awaiting_confirmation":
            if not confirmed:
                state["status"] = "failed"
                state["error"] = "Task cancelled by user."
                state["spoken_summary"] = "Understood. I have cancelled the pending operation."
                return state

            # Mark current step as confirmed and resume
            curr_idx = state["current_step_index"]
            if curr_idx < len(state["steps"]):
                state["steps"][curr_idx]["arguments"]["confirmed"] = True
            state["status"] = "executing"
            state["confirmation_proposal"] = None

        elif state["status"] == "awaiting_clarification":
            if user_input:
                curr_idx = state["current_step_index"]
                if curr_idx < len(state["steps"]):
                    state["steps"][curr_idx]["arguments"]["user_clarification"] = user_input
            state["status"] = "executing"
            state["clarification_question"] = None

        return await self._run_execution_loop(state)

    async def _run_execution_loop(self, state: ComplexTaskState) -> ComplexTaskState:
        """Execute remaining task steps sequentially until completion or pause."""
        steps = state["steps"]
        while state["current_step_index"] < len(steps):
            idx = state["current_step_index"]
            step = steps[idx]
            step["status"] = "in_progress"

            logger.info(f"[{state['task_id']}] Executing step {idx + 1}/{len(steps)}: {step['description']} ({step['tool_name']})")

            # Execute step via unified ToolRegistry
            tool_res = await tool_registry.execute_tool(
                tool_name=step["tool_name"],
                arguments=step["arguments"],
                user_id=state["user_id"],
                session_id=state["session_id"],
            )

            step["result"] = tool_res

            # Check if step triggered write confirmation pause
            if tool_res.get("status") == "confirmation_required" or tool_res.get("requires_confirmation"):
                step["status"] = "requires_confirmation"
                state["status"] = "awaiting_confirmation"
                state["confirmation_proposal"] = tool_res.get("message") or f"Please confirm before I execute {step['description']}."
                state["spoken_summary"] = state["confirmation_proposal"]
                logger.info(f"[{state['task_id']}] Paused for confirmation on step {idx + 1}")
                return state

            # Check for failures
            if tool_res.get("status") == "error":
                step["status"] = "failed"
                state["status"] = "failed"
                state["error"] = tool_res.get("error", "Step execution failed.")
                state["spoken_summary"] = f"I ran into an issue while trying to {step['description'].lower()}. {tool_res.get('error', '')}"
                return state

            # Success
            step["status"] = "completed"
            state["collected_results"][f"step_{idx + 1}_{step['tool_name']}"] = tool_res
            state["current_step_index"] += 1

        # All steps completed successfully
        state["status"] = "completed"
        state["spoken_summary"] = self._synthesize_summary(state)
        logger.info(f"[{state['task_id']}] Complex task completed successfully.")
        return state

    def _synthesize_summary(self, state: ComplexTaskState) -> str:
        """Synthesize natural 2-4 sentence spoken summary of completed complex workflow."""
        completed_steps = [s for s in state["steps"] if s["status"] == "completed"]
        goal = state["goal"]
        return f"I've completed your task for '{goal}'. All {len(completed_steps)} steps finished successfully."


complex_task_engine = ComplexTaskEngine()
