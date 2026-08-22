from typing import Any, TypedDict

class AgentState(TypedDict, total=False):
    session_id: str
    user_id: str
    messages: list[Any]
    current_transcript: str
    available_tools: list[Any]
    selected_tool: str | None
    tool_results: list[Any]
    memory_context: list[Any]
    persona: dict[str, Any]
    response: str
    generation_id: int
