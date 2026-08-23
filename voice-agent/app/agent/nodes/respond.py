"""Respond node: finalizes voice output and strips unsafe formatting."""

from typing import Any, Dict
from app.agent.state import AgentState
from app.shared.utils import clean_voice_text


async def respond_node(state: AgentState) -> Dict[str, Any]:
    """Clean and prepare text for TTS vocalization."""
    raw_response = state.get("response_text", "")
    cleaned = clean_voice_text(raw_response)

    return {"response_text": cleaned}
