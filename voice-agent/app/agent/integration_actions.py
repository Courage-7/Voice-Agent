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

    wants_search = bool(re.search(r"\b(search the web|search online|search google|look up online|latest news on|latest updates? on)\b", text))
    if wants_search:
        search_query = re.sub(r"^(?:please\s+)?(?:search\s+(?:the\s+web|online|google)?(?:\s+for)?|look\s+up\s+online(?:\s+for)?|latest\s+(?:news|updates?)\s+on)\s+", "", text, flags=re.IGNORECASE).strip()
        actions.append(PlannedIntegrationAction(
            tool_name="web_search_serpapi",
            arguments={"query": search_query or text},
            capability="search",
            required_app="SERPAPI",
        ))

    wants_drive = bool(re.search(r"\b(google drive|drive|my drive)\b", text)) and bool(re.search(r"\b(search|find|list|locate|files?|docs?|documents?)\b", text))
    if wants_drive:
        drive_query = re.sub(r"^(?:please\s+)?(?:search\s+(?:google\s+drive|my\s+drive|drive)?(?:\s+for)?|find\s+(?:files?|documents?|docs?)?(?:\s+in\s+drive)?)\s+", "", text, flags=re.IGNORECASE).strip()
        actions.append(PlannedIntegrationAction(
            tool_name="search_google_drive",
            arguments={"query": drive_query or text, "max_results": 5},
            capability="workspace",
            required_app="GOOGLEDRIVE",
        ))

    wants_notion = bool(re.search(r"\bnotion\b", text)) and bool(re.search(r"\b(search|find|look\s+up|pages?|notes?)\b", text))
    if wants_notion:
        notion_query = re.sub(r"^(?:please\s+)?(?:search\s+notion(?:\s+for)?|find\s+in\s+notion|look\s+up\s+in\s+notion)\s+", "", text, flags=re.IGNORECASE).strip()
        actions.append(PlannedIntegrationAction(
            tool_name="execute_app_action",
            arguments={"app_name": "notion", "intent": "search", "parameters": {"query": notion_query or text}},
            capability="workspace",
            required_app="NOTION",
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


def format_integration_response(execution: Dict[str, Any], filler_spoken: bool = False) -> str:
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
                lead = "Found them. " if filler_spoken else ""
                parts.append(f"{lead}Recent email: {lines}.")
            else:
                parts.append(result.get("spoken_summary", "No recent emails found."))
        elif result["tool_name"] == "list_calendar_events":
            events = result.get("events", [])
            if events:
                lines = "; ".join(f"{event.get('title', 'Untitled Meeting')} at {event.get('start', 'the scheduled time')}" for event in events[:5])
                lead = "Here is what's on your schedule. " if filler_spoken else ""
                parts.append(f"{lead}Upcoming calendar events: {lines}.")
            else:
                parts.append(result.get("spoken_summary", "No upcoming calendar events found."))
        elif result["tool_name"] in ("web_search_serpapi", "tavily_search"):
            res = result.get("results") or result.get("data")
            if res:
                if isinstance(res, list):
                    summary = "; ".join(str(item) for item in res[:3])
                else:
                    summary = str(res)
                lead = "Here is what I found online: " if filler_spoken else "Search results: "
                parts.append(f"{lead}{summary}")
            else:
                parts.append(result.get("spoken_summary", "No search results found."))
        elif result["tool_name"] == "search_google_drive":
            files = result.get("files", [])
            if files:
                lines = "; ".join(f"{f.get('name', 'Untitled')}" for f in files[:5])
                lead = "Found these files on Google Drive: " if filler_spoken else "Google Drive files: "
                parts.append(f"{lead}{lines}.")
            else:
                parts.append(result.get("spoken_summary", "No matching files found on Google Drive."))
        elif result["tool_name"] == "execute_app_action":
            parts.append(result.get("spoken_summary") or "Action on connected app completed.")
    return " ".join(parts) or "I couldn't complete the requested integration actions."
