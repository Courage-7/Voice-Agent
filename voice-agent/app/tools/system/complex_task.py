"""Tool to execute multi-step complex workflows through the LangGraph Complex Task Engine."""

from typing import Any, Dict
from app.tools.base import BaseTool


class RunComplexTaskTool(BaseTool):
    """Tool enabling the agent to trigger composite, multi-step workflows across workspace apps."""

    name: str = "run_complex_task"
    description: str = (
        "Execute a multi-step composite workflow across tools and connected apps (e.g. "
        "searching emails and compiling findings into a document, or cross-referencing research and scheduling)."
    )
    capability: str = "system"
    read_only: bool = False
    requires_confirmation: bool = False

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "The high-level composite goal to plan and execute.",
            },
            "context": {
                "type": "object",
                "description": "Optional parameters, search terms, or target entities for the task.",
            },
        },
        "required": ["goal"],
    }

    async def execute(
        self,
        goal: str,
        context: Dict[str, Any] | None = None,
        user_id: str = "default_user",
        session_id: str = "",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute complex task via ComplexTaskEngine."""
        from app.agent.complex_tasks.engine import complex_task_engine

        task_state = await complex_task_engine.start_task(
            goal=goal,
            user_id=user_id,
            session_id=session_id,
            context=context or {},
        )

        return {
            "status": task_state["status"],
            "task_id": task_state["task_id"],
            "spoken_summary": task_state.get("spoken_summary"),
            "confirmation_proposal": task_state.get("confirmation_proposal"),
            "steps_count": len(task_state.get("steps", [])),
            "results": task_state.get("collected_results", {}),
        }
