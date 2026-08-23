"""System tool to retrieve current date, time, and timezone in spoken format."""

from datetime import datetime
from typing import Any, Dict
from zoneinfo import ZoneInfo

from app.tools.base import BaseTool


class CurrentTimeTool(BaseTool):
    """Tool to provide accurate current local time and date."""

    name = "get_current_time"
    description = "Get the current time, date, and day of the week formatted for natural speech."
    capability = "system"
    read_only = True
    requires_confirmation = False
    timeout_seconds = 5.0

    parameters = {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Optional IANA timezone name (e.g. 'America/New_York', 'UTC'). Defaults to UTC.",
            }
        },
        "required": [],
    }

    async def execute(self, timezone: str = "UTC", **kwargs: Any) -> Dict[str, Any]:
        try:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)
        except Exception:
            now = datetime.now()

        formatted_time = now.strftime("%I:%M %p")
        formatted_date = now.strftime("%A, %B %d, %Y")

        return {
            "success": True,
            "spoken_time": f"It is currently {formatted_time} on {formatted_date}.",
            "iso_time": now.isoformat(),
            "timezone": str(now.tzinfo),
        }
