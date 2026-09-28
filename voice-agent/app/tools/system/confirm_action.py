"""Tool to confirm pending actions or resume multi-step complex workflows."""

import logging
from typing import Any, Dict, Optional
from app.tools.base import BaseTool
from app.tools.pending_actions import pending_action_store

logger = logging.getLogger(__name__)


class ConfirmActionTool(BaseTool):
    """Tool enabling the agent to confirm and execute pending actions or resume paused tasks."""

    name: str = "confirm_pending_action"
    description: str = (
        "Confirm a previously proposed write action or resume a paused complex task "
        "once the user has verbally granted permission."
    )
    capability: str = "system"
    read_only: bool = False
    requires_confirmation: bool = False

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "action_id": {
                "type": "string",
                "description": "Optional ID of the specific pending action to approve or decline.",
            },
            "task_id": {
                "type": "string",
                "description": "Optional ID of a paused complex task to resume.",
            },
            "confirmed": {
                "type": "boolean",
                "description": "True if the user confirmed/approved; false if cancelled/rejected.",
            },
            "user_input": {
                "type": "string",
                "description": "Optional clarification text or instructions provided by the user.",
            },
        },
        "required": ["confirmed"],
    }

    async def execute(
        self,
        confirmed: bool = True,
        action_id: Optional[str] = None,
        task_id: Optional[str] = None,
        user_input: Optional[str] = None,
        user_id: str = "default_user",
        session_id: str = "",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Resume task or confirm and execute pending action."""
        # 1. Complex Task Resume / Cancellation Path
        if task_id:
            from app.agent.complex_tasks.engine import complex_task_engine
            task = complex_task_engine.get_task(task_id)
            if task:
                resumed = await complex_task_engine.resume_task(
                    task_id=task_id,
                    user_input=user_input,
                    confirmed=confirmed,
                    user_id=user_id,
                )
                return {
                    "success": resumed["status"] in ("completed", "executing", "awaiting_confirmation"),
                    "status": resumed["status"],
                    "task_id": task_id,
                    "spoken_summary": resumed.get("spoken_summary") or ("Action resumed." if confirmed else "Action cancelled."),
                }

        # 2. User declined / cancelled the action
        if not confirmed:
            target_id = action_id
            if not target_id:
                latest = await pending_action_store.get_latest_for_session(session_id, user_id)
                if latest:
                    target_id = latest.action_id
            if target_id:
                await pending_action_store.cancel(target_id, user_id, session_id)
            return {
                "success": True,
                "cancelled": True,
                "spoken_summary": "Understood. I have cancelled the operation.",
            }

        # 3. User approved: Locate pending action record
        target_action = None
        if action_id:
            target_action = await pending_action_store.get(action_id, user_id)
        else:
            target_action = await pending_action_store.get_latest_for_session(session_id, user_id)

        if not target_action or target_action.consumed or target_action.is_expired():
            logger.warning(
                f"Confirmation attempted without active pending action (user={user_id}, session={session_id}, action_id={action_id})"
            )
            return {
                "success": False,
                "error": "No pending action found requiring confirmation.",
                "spoken_summary": "There is no action waiting for your confirmation.",
            }

        # 4. Execute the authorized tool via ToolRegistry with verified action_id
        from app.tools.registry import tool_registry
        return await tool_registry.execute_tool(
            tool_name=target_action.tool_name,
            arguments=target_action.arguments,
            user_id=user_id,
            session_id=session_id,
            confirmed=True,
            action_id=target_action.action_id,
        )
