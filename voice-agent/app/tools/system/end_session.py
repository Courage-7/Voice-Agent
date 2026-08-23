"""System tool to gracefully end a voice conversation session."""

import logging
from typing import Any, Dict
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class EndVoiceSessionTool(BaseTool):
    """Tool to gracefully terminate an active voice session."""

    name = "end_voice_session"
    description = "End the current voice conversation session when the user says goodbye, asks to stop, exit, leave, disconnect, or end the call."
    capability = "system"
    read_only = True
    requires_confirmation = False
    timeout_seconds = 5.0

    parameters = {
        "type": "object",
        "properties": {
            "farewell_message": {
                "type": "string",
                "description": "Short polite parting phrase (e.g. 'Goodbye! Have a great day.')",
            }
        },
        "required": [],
    }

    async def execute(self, farewell_message: str = "Goodbye! Have a great day.", **kwargs: Any) -> Dict[str, Any]:
        session_id = kwargs.get("session_id", "")
        logger.info(f"Ending voice session requested: session_id={session_id}")
        return {
            "success": True,
            "end_session": True,
            "spoken_summary": farewell_message,
            "message": "Session terminated by user request.",
        }
