"""Complex task state schema for multi-step LangGraph orchestration."""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class TaskStep(TypedDict):
    step_id: int
    description: str
    tool_name: str
    arguments: Dict[str, Any]
    status: str  # "pending", "in_progress", "completed", "failed", "requires_confirmation"
    result: Optional[Dict[str, Any]]


class ComplexTaskState(TypedDict):
    """Execution state tracked across multi-step LangGraph task workflows."""

    task_id: str
    user_id: str
    session_id: str
    goal: str
    steps: List[TaskStep]
    current_step_index: int
    collected_results: Dict[str, Any]
    status: str  # "planning", "executing", "awaiting_confirmation", "awaiting_clarification", "completed", "failed"
    clarification_question: Optional[str]
    confirmation_proposal: Optional[str]
    spoken_summary: Optional[str]
    error: Optional[str]
