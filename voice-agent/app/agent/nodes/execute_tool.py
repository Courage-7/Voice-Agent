"""Execute tool node: invokes registered tools via ToolRegistry."""

from typing import Any, Dict
from app.agent.state import AgentState
from app.tools.registry import tool_registry


async def execute_tool_node(state: AgentState) -> Dict[str, Any]:
    """Execute active tool call."""
    tool_call = state.get("active_tool_call")
    if not tool_call:
        return {"tool_result": None}

    tool_name = tool_call.get("name", "")
    args = tool_call.get("arguments", {})

    result = await tool_registry.execute_tool(
        tool_name=tool_name,
        arguments=args,
        user_id=state.get("user_id", "default_user"),
        session_id=state.get("session_id", ""),
    )

    return {"tool_result": result}
