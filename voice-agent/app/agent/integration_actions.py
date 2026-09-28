"""Connection-gated execution for integration requests.

Connection discovery is deliberately only a precondition here.  Every planned
read action is bound to the user-scoped registry and executed before a response
is generated; it is never treated as the answer to the user's request.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.agent.task_execution import CapabilityTask, capability_execution_engine

ActivityCallback = Callable[[Dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class PlannedIntegrationAction:
    tool_name: str
    arguments: Dict[str, Any]
    capability: str
    required_app: str


def plan_integration_actions(user_text: str) -> List[PlannedIntegrationAction]:
    """Extract the supported read actions requested in a single user turn."""
    text = user_text.lower()
    actions: List[PlannedIntegrationAction] = []

    wants_email = bool(re.search(r"\b(gmail|email(?:s)?|inbox|messages?)\b", text))
    wants_calendar = bool(re.search(r"\b(calendar|events?|meetings?|schedule)\b", text))

    if wants_email:
        # Composio/Gmail accepts Gmail search syntax; this is intentionally a
        # bounded default for "recent" requests instead of an unfiltered inbox.
        query = "newer_than:7d" if re.search(r"\b(recent|latest|new|inbox|messages?)\b", text) else ""
        actions.append(PlannedIntegrationAction(
            tool_name="search_emails",
            arguments={"query": query, "max_results": 5, "provider": "gmail"} if "gmail" in text else {"query": query, "max_results": 5},
            capability="email",
            required_app="GMAIL" if "gmail" in text else "",
        ))

    if wants_calendar:
        actions.append(PlannedIntegrationAction(
            tool_name="list_calendar_events",
            arguments={"max_events": 10, "provider": "google"} if "google" in text else {"max_events": 10},
            capability="calendar",
            required_app="GOOGLECALENDAR" if "google" in text else "",
        ))

    return actions


async def execute_requested_integration_actions(
    user_text: str,
    user_id: str,
    session_id: str,
    on_activity: Optional[ActivityCallback] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve, bind, and execute all integration actions requested in a turn.

    ``None`` means the turn did not request a supported integration action. A
    non-None value always represents a completed plan (including connection or
    execution failures) and therefore must not be sent back to an LLM to invent
    a contradictory access answer.
    """
    actions = plan_integration_actions(user_text)
    if not actions:
        return None

    # This remains a thin, domain-specific intent adapter. Provider selection,
    # connected-account filtering, execution, validation, and activity logging
    # are delegated to the provider-agnostic capability execution engine.
    tasks = [
        CapabilityTask(
            goal=("retrieve recent messages" if action.capability == "email" else "retrieve upcoming events"),
            tool_name=action.tool_name,
            capability=action.capability,
            arguments=action.arguments,
            allows_empty=True,
        )
        for action in actions
    ]
    execution = await capability_execution_engine.execute(
        tasks,
        user_id=user_id,
        session_id=session_id,
        on_activity=on_activity,
    )
    return {
        "connected_apps": execution.connected_apps,
        "results": [
            {"tool_name": task.tool_name, "task_id": task.id, "task_state": task.state.value, **(task.result or {})}
            for task in execution.tasks
        ],
    }


def format_integration_response(execution: Dict[str, Any]) -> str:
    """Return an evidence-based combined response for the completed actions."""
    parts: List[str] = []
    for result in execution["results"]:
        if not result.get("success"):
            parts.append(result.get("spoken_summary") or result.get("error") or "The connected service could not complete that request.")
            continue
        if result["tool_name"] == "search_emails":
            emails = result.get("emails", [])
            if emails:
                lines = "; ".join(f"{email.get('sender', 'Unknown')}: {email.get('subject', 'No subject')}" for email in emails[:5])
                parts.append(f"Recent email: {lines}.")
            else:
                parts.append(result.get("spoken_summary", "No recent emails found."))
        elif result["tool_name"] == "list_calendar_events":
            events = result.get("events", [])
            if events:
                lines = "; ".join(f"{event.get('title', 'Untitled Meeting')} at {event.get('start', 'the scheduled time')}" for event in events[:5])
                parts.append(f"Upcoming calendar events: {lines}.")
            else:
                parts.append(result.get("spoken_summary", "No upcoming calendar events found."))
    return " ".join(parts) or "I couldn't complete the requested integration actions."
