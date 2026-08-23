"""Calendar tools: Google Calendar and Outlook Calendar integrations via Composio."""

from typing import Any, Dict, List, Optional
from app.integrations.composio.client import composio_gateway
from app.tools.base import BaseTool


def _extract_raw_events(raw_data: Any) -> List[Dict[str, Any]]:
    """Extract event items safely from varying Composio response schemas."""
    if isinstance(raw_data, list):
        return [e for e in raw_data if isinstance(e, dict)]
    if not isinstance(raw_data, dict):
        return []

    inner = raw_data.get("data") or raw_data.get("response_data") or raw_data
    if isinstance(inner, dict):
        events = inner.get("items") or inner.get("events") or []
        return [e for e in events if isinstance(e, dict)]
    if isinstance(inner, list):
        return [e for e in inner if isinstance(e, dict)]
    return []


def _format_compact_events(raw_events: List[Dict[str, Any]], max_events: int) -> List[Dict[str, str]]:
    """Format raw calendar events into compact dictionaries for LLM speech."""
    compact_events: List[Dict[str, str]] = []
    for ev in raw_events[:max_events]:
        title = str(ev.get("summary") or ev.get("title") or "Untitled Meeting")[:80]
        start_obj = ev.get("start", {})
        if isinstance(start_obj, dict):
            start_val = start_obj.get("dateTime") or start_obj.get("date") or "Scheduled"
        else:
            start_val = str(start_obj)
        compact_events.append({"title": title, "start": str(start_val)[:40]})
    return compact_events


class CreateCalendarEventTool(BaseTool):
    """Tool to create events on Google Calendar or Outlook."""

    name = "create_calendar_event"
    description = "Create a new meeting or calendar event on Google Calendar or Outlook."
    capability = "calendar"
    read_only = False
    requires_confirmation = True
    timeout_seconds = 15.0

    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "The title or subject of the event."},
            "start_time": {"type": "string", "description": "Start time in ISO format or natural date/time."},
            "duration_minutes": {"type": "integer", "description": "Duration in minutes. Defaults to 30."},
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of attendee email addresses.",
            },
            "provider": {"type": "string", "enum": ["google", "outlook"], "description": "Calendar provider."},
        },
        "required": ["title", "start_time"],
    }

    async def execute(
        self,
        title: str,
        start_time: str,
        duration_minutes: int = 30,
        attendees: Optional[list] = None,
        provider: str = "google",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", "default_user")
        action_name = "GOOGLECALENDAR_CREATE_EVENT" if provider.lower() == "google" else "OUTLOOK_CREATE_EVENT"
        params = {
            "summary": title,
            "start_time": start_time,
            "duration": duration_minutes,
            "attendees": attendees or [],
        }

        res = await composio_gateway.execute_action(action_name, params, entity_id=user_id)
        if res.get("success"):
            return {
                "success": True,
                "spoken_summary": f"I have scheduled '{title}' for {start_time}.",
                "event": res,
            }
        return {
            "success": False,
            "error": res.get("error", "Failed to schedule event"),
            "spoken_summary": f"I was unable to create the calendar event '{title}'.",
        }


class ListCalendarEventsTool(BaseTool):
    """Tool to list upcoming events and check calendar availability."""

    name = "list_calendar_events"
    description = "List upcoming meetings and check calendar availability for a given time window."
    capability = "calendar"
    read_only = True
    requires_confirmation = False
    timeout_seconds = 10.0

    parameters = {
        "type": "object",
        "properties": {
            "time_min": {"type": "string", "description": "Start of search window in ISO 8601 or natural date."},
            "time_max": {"type": "string", "description": "End of search window in ISO 8601 or natural date."},
            "max_events": {"type": "integer", "description": "Maximum events to return. Defaults to 10."},
            "provider": {"type": "string", "enum": ["google", "outlook"], "description": "Calendar provider."},
        },
        "required": [],
    }

    async def execute(
        self,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_events: int = 10,
        provider: str = "google",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", "default_user")
        action_name = "GOOGLECALENDAR_FIND_EVENT" if provider.lower() == "google" else "OUTLOOK_GET_CALENDAR_VIEW"
        params: Dict[str, Any] = {}
        if time_min:
            params["time_min"] = time_min
        if time_max:
            params["time_max"] = time_max
        if max_events:
            params["max_results"] = max_events

        res = await composio_gateway.execute_action(action_name, params, entity_id=user_id)
        if not res.get("success"):
            return {
                "success": False,
                "spoken_summary": res.get("spoken_summary", "Unable to retrieve calendar events."),
                "error": res.get("error", "Calendar query failed"),
            }

        raw_events = _extract_raw_events(res.get("data", {}))
        compact_events = _format_compact_events(raw_events, max_events)

        count = len(compact_events)
        if count == 1:
            summary = "Found 1 upcoming event on your calendar."
        elif count > 1:
            summary = f"Found {count} upcoming events on your calendar."
        else:
            summary = "No upcoming events found on your calendar."

        return {
            "success": True,
            "count": count,
            "spoken_summary": summary,
            "events": compact_events,
        }
