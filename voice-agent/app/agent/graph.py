"""LangGraph state graph definition and compilation with graceful fallback."""

import logging
from typing import Any, Dict

from app.agent.nodes.execute_tool import execute_tool_node
from app.agent.nodes.load_context import load_context_node
from app.agent.nodes.reason import reason_node
from app.agent.nodes.respond import respond_node
from app.agent.state import AgentState

logger = logging.getLogger(__name__)


class FallbackAgentRunner:
    """Fallback runner when langgraph package is not yet installed."""

    async def ainvoke(self, state: AgentState) -> AgentState:
        current_state = dict(state)

        # 1. Load context
        ctx = await load_context_node(current_state)
        current_state.update(ctx)

        # 2. Reason
        reason_res = await reason_node(current_state)
        current_state.update(reason_res)

        # 3. Tool execution if active
        if current_state.get("active_tool_call"):
            tool_res = await execute_tool_node(current_state)
            current_state.update(tool_res)
            # Second reason turn
            reason_res2 = await reason_node(current_state)
            current_state.update(reason_res2)

        # 4. Respond
        respond_res = await respond_node(current_state)
        current_state.update(respond_res)

        return current_state


def build_agent_graph() -> Any:
    """Build and compile the multi-turn conversational LangGraph."""
    try:
        from langgraph.graph import END, StateGraph

        builder = StateGraph(AgentState)

        # Add Nodes
        builder.add_node("load_context", load_context_node)
        builder.add_node("reason", reason_node)
        builder.add_node("execute_tool", execute_tool_node)
        builder.add_node("respond", respond_node)

        # Set Entry Point
        builder.set_entry_point("load_context")

        # Connect Edges
        builder.add_edge("load_context", "reason")

        def route_reason_output(state: AgentState) -> str:
            if state.get("active_tool_call"):
                return "execute_tool"
            return "respond"

        builder.add_conditional_edges(
            "reason",
            route_reason_output,
            {"execute_tool": "execute_tool", "respond": "respond"},
        )
        builder.add_edge("execute_tool", "reason")
        builder.add_edge("respond", END)

        logger.info("Compiled LangGraph Agent StateGraph.")
        return builder.compile()

    except ImportError:
        logger.warning("LangGraph not installed in environment. Using FallbackAgentRunner.")
        return FallbackAgentRunner()


agent_graph = build_agent_graph()
