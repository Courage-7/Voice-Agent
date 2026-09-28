"""LangGraph state graph definition for the server-side execution owner."""

import logging
from typing import Any

from app.agent.nodes.execute_tool import execute_tool_node
from app.agent.nodes.load_context import load_context_node
from app.agent.nodes.resolve_integrations import resolve_integrations_node
from app.agent.nodes.reason import reason_node
from app.agent.nodes.respond import respond_node
from app.agent.state import AgentState

logger = logging.getLogger(__name__)


def build_agent_graph() -> Any:
    """Build the authoritative multi-turn conversational LangGraph.

    LangGraph is a required runtime dependency.  A silent procedural fallback
    would create a second, differently-behaving execution engine.
    """
    from langgraph.graph import END, StateGraph

    builder = StateGraph(AgentState)

    builder.add_node("load_context", load_context_node)
    builder.add_node("resolve_integrations", resolve_integrations_node)
    builder.add_node("reason", reason_node)
    builder.add_node("execute_tool", execute_tool_node)
    builder.add_node("respond", respond_node)

    builder.set_entry_point("load_context")
    builder.add_edge("load_context", "resolve_integrations")

    def route_integration_resolution(state: AgentState) -> str:
        return "respond" if state.get("integration_handled") else "reason"

    builder.add_conditional_edges(
        "resolve_integrations",
        route_integration_resolution,
        {"reason": "reason", "respond": "respond"},
    )

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


agent_graph = build_agent_graph()
