"""Respond node: finalizes voice output, preserving markdown for display and cleaning speech for TTS."""

from typing import Any, Dict
from app.agent.state import AgentState
from app.shared.utils import clean_voice_text, extract_dual_stream_tags


def respond_node(state: AgentState) -> Dict[str, Any]:
    """Clean and prepare dual-channel text: rich markdown for display and plain prose for TTS."""
    raw_response = state.get("response_text", "")
    display_md, speech_txt = extract_dual_stream_tags(raw_response)

    return {
        "response_text": display_md,
        "display_markdown": display_md,
        "speech_text": speech_txt,
    }
