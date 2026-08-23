"""LangGraph agent state schema."""

from typing import Annotated, Any, Dict, List, Optional, Sequence
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """Complete conversational state tracked across LangGraph nodes."""

    session_id: str
    user_id: str
    messages: List[Dict[str, Any]]
    memory_context: str
    user_context: str
    active_tool_call: Optional[Dict[str, Any]]
    tool_result: Optional[Dict[str, Any]]
    response_text: str
    error: Optional[str]
