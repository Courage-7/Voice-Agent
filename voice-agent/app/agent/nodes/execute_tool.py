"""Execute tool node: invokes registered tools via ToolRegistry."""

from typing import Any, Dict, Optional
from langchain_core.runnables import RunnableConfig
from app.agent.state import AgentState
from app.tools.registry import tool_registry


async def execute_tool_node(state: AgentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Execute active tool call with optional activity callback."""
    tool_call = state.get("active_tool_call")
    if not tool_call:
        return {"tool_result": None}

    tool_name = tool_call.get("name", "")
    args = tool_call.get("arguments", {})

    on_activity = None
    if config and isinstance(config, dict):
        on_activity = config.get("configurable", {}).get("on_activity")

    if on_activity:
        try:
            import inspect
            evt = {"type": "ToolExecuting", "tool": tool_name}
            if inspect.iscoroutinefunction(on_activity):
                await on_activity(evt)
            else:
                on_activity(evt)
        except Exception:
            pass

    result = await tool_registry.execute_tool(
        tool_name=tool_name,
        arguments=args,
        user_id=state.get("user_id", "default_user"),
        session_id=state.get("session_id", ""),
    )

    return {"tool_result": result, "active_tool_call": None}

