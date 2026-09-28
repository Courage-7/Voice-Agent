"""LangGraph precondition node for connected integration work."""

from typing import Any, Dict

from app.agent.integration_actions import (
    execute_requested_integration_actions,
    format_integration_response,
)
from app.agent.state import AgentState


async def resolve_integrations_node(state: AgentState) -> Dict[str, Any]:
    """Execute requested integration reads before the free-form reasoning node.

    This keeps connection resolution, tool binding, and execution in the graph
    rather than allowing a planner to treat ``get_connected_apps`` as terminal.
    """
    user_messages = [message.get("content", "") for message in state.get("messages", []) if message.get("role") == "user"]
    if not user_messages:
        return {"integration_handled": False}

    execution = await execute_requested_integration_actions(
        user_text=user_messages[-1],
        user_id=state.get("user_id", "default_user"),
        session_id=state.get("session_id", ""),
    )
    if execution is None:
        return {"integration_handled": False}
    return {
        "integration_handled": True,
        "tool_result": execution,
        "response_text": format_integration_response(execution),
        "active_tool_call": None,
    }
