"""Complex Task Execution Engine with pause/resume and safety confirmation."""

import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from app.agent.complex_tasks.planner import complex_task_planner
from app.agent.complex_tasks.state import ComplexTaskState
from app.tools.registry import tool_registry

logger = logging.getLogger(__name__)


import asyncio
from datetime import datetime, timezone
from app.db.session import db_gateway


class ComplexTaskEngine:
    """Orchestrates multi-step workflows using LangGraph patterns with unified safety boundaries."""

    def __init__(self, max_tasks: int = 200) -> None:
        self._active_tasks: Dict[str, ComplexTaskState] = {}
        self._max_tasks = max_tasks

    def _prune_tasks_if_needed(self) -> None:
        """Evict oldest tasks if memory exceeds max limit."""
        if len(self._active_tasks) > self._max_tasks:
            # Drop oldest half of terminal tasks
            terminal = [
                tid for tid, s in self._active_tasks.items()
                if s["status"] in ("completed", "failed")
            ]
            for tid in terminal[: len(self._active_tasks) - self._max_tasks]:
                self._active_tasks.pop(tid, None)

    async def _save_checkpoint(self, state: ComplexTaskState) -> None:
        """Persist task checkpoint to Neon PostgreSQL if connected."""
        task_id = state["task_id"]
        self._active_tasks[task_id] = state
        self._prune_tasks_if_needed()

        if db_gateway.is_connected:
            try:
                query = """
                INSERT INTO tasks (
                    task_id, user_id, session_id, goal, status,
                    current_step, total_steps, steps, results,
                    spoken_summary, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, now())
                ON CONFLICT (task_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    session_id = EXCLUDED.session_id,
                    goal = EXCLUDED.goal,
                    status = EXCLUDED.status,
                    current_step = EXCLUDED.current_step,
                    total_steps = EXCLUDED.total_steps,
                    steps = EXCLUDED.steps,
                    results = EXCLUDED.results,
                    spoken_summary = EXCLUDED.spoken_summary,
                    updated_at = now()
                """
                await db_gateway.execute_as_user(
                    state["user_id"],
                    query,
                    state["task_id"],
                    state["user_id"],
                    state.get("session_id", ""),
                    state["goal"],
                    state["status"],
                    state["current_step_index"],
                    len(state["steps"]),
                    state["steps"],
                    state["collected_results"],
                    state.get("spoken_summary"),
                )
            except Exception as e:
                logger.warning(f"Failed to persist task checkpoint for {task_id} to Neon PostgreSQL: {e}")

    def get_task(self, task_id: str) -> Optional[ComplexTaskState]:
        """Retrieve task state by task ID."""
        return self._active_tasks.get(task_id)

    async def get_task_async(self, task_id: str, user_id: Optional[str] = None) -> Optional[ComplexTaskState]:
        """Retrieve task state by task ID, hydrating from Neon PostgreSQL on fresh process or cache miss."""
        state = self.get_task(task_id)
        if state and (user_id is None or state["user_id"] == user_id):
            return state

        if db_gateway.is_connected:
            try:
                if not user_id:
                    return None
                row = await db_gateway.fetchrow_as_user(
                    user_id,
                    "SELECT * FROM tasks WHERE task_id = $1 LIMIT 1",
                    task_id,
                )
                if row:
                    row_dict = dict(row)
                    hydrated_state: ComplexTaskState = {
                        "task_id": row_dict["task_id"],
                        "user_id": row_dict["user_id"],
                        "session_id": row_dict.get("session_id", ""),
                        "goal": row_dict["goal"],
                        "steps": row_dict.get("steps") or [],
                        "current_step_index": row_dict.get("current_step", 0),
                        "collected_results": row_dict.get("results") or {},
                        "status": row_dict.get("status", "executing"),
                        "clarification_question": None,
                        "confirmation_proposal": None,
                        "spoken_summary": row_dict.get("spoken_summary"),
                        "error": None,
                    }
                    self._active_tasks[task_id] = hydrated_state
                    return hydrated_state
            except Exception as e:
                logger.warning(f"Failed to hydrate task {task_id} from Neon PostgreSQL: {e}")

        return None

    async def start_task(
        self,
        goal: str,
        user_id: str = "default_user",
        session_id: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> ComplexTaskState:
        """Initialize and execute a new complex multi-step task."""
        task_id = f"task_{uuid4().hex[:8]}"
        steps = await complex_task_planner.plan_steps(
            goal=goal,
            context=context or {},
            user_id=user_id,
        )

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
        await self._save_checkpoint(state)

        return await self._run_execution_loop(state)

    async def resume_task(
        self,
        task_id: str,
        user_input: Optional[str] = None,
        confirmed: bool = False,
        user_id: Optional[str] = None,
    ) -> ComplexTaskState:
        """Resume a paused complex task after user confirmation or clarification."""
        state = await self.get_task_async(task_id, user_id=user_id)
        if not state:
            raise ValueError(f"Complex task '{task_id}' not found.")

        if state["status"] == "awaiting_confirmation":
            if not confirmed:
                state["status"] = "failed"
                state["error"] = "Task cancelled by user."
                state["spoken_summary"] = "Understood. I have cancelled the pending operation."
                await self._save_checkpoint(state)
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

        await self._save_checkpoint(state)
        return await self._run_execution_loop(state)

    async def _run_execution_loop(self, state: ComplexTaskState) -> ComplexTaskState:
        """Execute remaining task steps sequentially until completion or pause."""
        steps = state["steps"]
        while state["current_step_index"] < len(steps):
            idx = state["current_step_index"]
            step = steps[idx]
            step["status"] = "in_progress"

            # Resolve step arguments using collected results from prior steps (F05)
            resolved_args = self._resolve_step_arguments(
                step["arguments"],
                state["collected_results"],
                step["tool_name"],
            )
            step["arguments"] = resolved_args

            # Execute step via unified ToolRegistry
            tool_res = await tool_registry.execute_tool(
                tool_name=step["tool_name"],
                arguments=resolved_args,
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
                await self._save_checkpoint(state)
                return state

            # Check for failures: status == error/failed OR success is False
            is_failure = (
                tool_res.get("success") is False
                or tool_res.get("status") in ("error", "failed")
                or ("error" in tool_res and not tool_res.get("success"))
            )
            if is_failure:
                step["status"] = "failed"
                state["status"] = "failed"
                state["error"] = tool_res.get("error", "Step execution failed.")
                state["spoken_summary"] = f"I ran into an issue while trying to {step['description'].lower()}. {tool_res.get('error', '')}"
                await self._save_checkpoint(state)
                return state

            # Success
            step["status"] = "completed"
            state["collected_results"][f"step_{idx + 1}_{step['tool_name']}"] = tool_res
            state["current_step_index"] += 1
            await self._save_checkpoint(state)

        # All steps completed successfully
        state["status"] = "completed"
        state["spoken_summary"] = self._synthesize_summary(state)
        await self._save_checkpoint(state)
        logger.info(f"[{state['task_id']}] Complex task completed successfully.")
        return state

    def _resolve_step_arguments(
        self,
        arguments: Dict[str, Any],
        collected_results: Dict[str, Any],
        tool_name: str,
    ) -> Dict[str, Any]:
        """Propagate prior step results and outputs into downstream step arguments (Finding F05)."""
        resolved = dict(arguments)
        if not collected_results:
            return resolved

        # Find most recent step result
        last_key = list(collected_results.keys())[-1]
        last_result = collected_results[last_key]
        if not isinstance(last_result, dict):
            return resolved

        prior_text = ""
        if "results" in last_result and isinstance(last_result["results"], str):
            prior_text = last_result["results"]
        elif "data" in last_result:
            data = last_result["data"]
            if isinstance(data, str):
                prior_text = data
            elif isinstance(data, dict):
                prior_text = data.get("content") or data.get("results") or data.get("summary") or str(data)
        elif "emails" in last_result and isinstance(last_result["emails"], list):
            emails = last_result["emails"]
            prior_text = "\n".join(
                f"From: {e.get('from', e.get('sender', ''))} | Subject: {e.get('subject', '')} | Snippet: {e.get('snippet', '')}"
                for e in emails[:5]
            )
        elif "content" in last_result and isinstance(last_result["content"], str):
            prior_text = last_result["content"]
        elif "answer" in last_result and isinstance(last_result["answer"], str):
            prior_text = last_result["answer"]

        if prior_text:
            if tool_name == "manage_google_doc":
                curr_content = resolved.get("content", "")
                if not curr_content or any(p in curr_content.lower() for p in ("synthesized", "summary of", "findings...")):
                    resolved["content"] = prior_text
            elif tool_name == "manage_google_sheet":
                if "emails" in last_result and isinstance(last_result["emails"], list):
                    resolved["values"] = [
                        [e.get("subject", ""), e.get("from", e.get("sender", "")), e.get("date", "")]
                        for e in last_result["emails"][:10]
                    ]
            elif tool_name in ("send_email", "create_draft"):
                curr_body = resolved.get("body", "")
                if not curr_body or any(p in curr_body.lower() for p in ("placeholder", "summary", "drafted")):
                    resolved["body"] = prior_text

        return resolved

    def _synthesize_summary(self, state: ComplexTaskState) -> str:
        """Synthesize natural 2-4 sentence spoken summary of completed complex workflow."""
        completed_steps = [s for s in state["steps"] if s["status"] == "completed"]
        goal = state["goal"]
        return f"I've completed your task for '{goal}'. All {len(completed_steps)} steps finished successfully."


complex_task_engine = ComplexTaskEngine()

