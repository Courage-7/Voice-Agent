"""Dynamic Intent-Driven App Action Tool.

Dynamically maps and routes user intent to any available action across all connected apps
in the user's workspace (Gmail, Google Calendar, Sheets, Docs, Drive, Outlook, Search, etc.).
"""

import logging
from typing import Any, Dict, Optional
from app.integrations.composio.client import composio_gateway
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

# Common intent mappings to Composio action slugs
INTENT_SLUG_MAP = {
    # Gmail
    ("gmail", "fetch"): "GMAIL_FETCH_EMAILS",
    ("gmail", "search"): "GMAIL_FETCH_EMAILS",
    ("gmail", "list"): "GMAIL_FETCH_EMAILS",
    ("gmail", "read"): "GMAIL_FETCH_EMAILS",
    ("gmail", "send"): "GMAIL_SEND_EMAIL",
    ("gmail", "create_draft"): "GMAIL_CREATE_DRAFT",
    # Google Calendar
    ("googlecalendar", "find"): "GOOGLECALENDAR_FIND_EVENT",
    ("googlecalendar", "list"): "GOOGLECALENDAR_FIND_EVENT",
    ("googlecalendar", "search"): "GOOGLECALENDAR_FIND_EVENT",
    ("googlecalendar", "get"): "GOOGLECALENDAR_FIND_EVENT",
    ("googlecalendar", "create"): "GOOGLECALENDAR_CREATE_EVENT",
    ("googlecalendar", "free_slots"): "GOOGLECALENDAR_FIND_FREE_SLOTS",
    # Google Sheets
    ("googlesheets", "read"): "GOOGLESHEETS_BATCH_GET",
    ("googlesheets", "get"): "GOOGLESHEETS_BATCH_GET",
    ("googlesheets", "append"): "GOOGLESHEETS_APPEND_VALUES",
    ("googlesheets", "update"): "GOOGLESHEETS_UPDATE_VALUES",
    ("googlesheets", "create"): "GOOGLESHEETS_CREATE_SPREADSHEET",
    # Google Docs
    ("googledocs", "create"): "GOOGLEDOCS_CREATE_DOCUMENT",
    ("googledocs", "read"): "GOOGLEDOCS_GET_DOCUMENT",
    ("googledocs", "get"): "GOOGLEDOCS_GET_DOCUMENT",
    # Google Drive
    ("googledrive", "search"): "GOOGLEDRIVE_SEARCH_FILES",
    ("googledrive", "find"): "GOOGLEDRIVE_SEARCH_FILES",
    ("googledrive", "list"): "GOOGLEDRIVE_SEARCH_FILES",
    ("googledrive", "get"): "GOOGLEDRIVE_GET_FILE",
    # Outlook
    ("outlook", "fetch"): "OUTLOOK_GET_EMAILS",
    ("outlook", "search"): "OUTLOOK_GET_EMAILS",
    ("outlook", "send"): "OUTLOOK_SEND_MAIL",
    ("outlook", "calendar"): "OUTLOOK_GET_CALENDAR_VIEW",
    # Search
    ("serpapi", "search"): "SERPAPI_SEARCH",
    ("perplexityai", "search"): "PERPLEXITYAI_PERPLEXITY_AI_SEARCH",
}


WRITE_INTENTS = {"send", "create", "append", "update", "delete", "remove", "revoke"}


class ExecuteAppActionTool(BaseTool):
    """Universal intent-driven tool to execute actions across connected workspace apps."""

    name = "execute_app_action"
    description = (
        "Dynamically execute an action on any connected workspace app based on user intent. "
        "Supports Gmail, Google Calendar, Google Sheets, Google Docs, Google Drive, Outlook, and Search."
    )
    capability = "workspace"
    read_only = False
    requires_confirmation = False  # Checked dynamically at execution boundary based on resolved intent
    timeout_seconds = 20.0

    parameters = {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "enum": ["gmail", "googlecalendar", "googlesheets", "googledocs", "googledrive", "outlook", "serpapi", "perplexityai"],
                "description": "The connected app to interact with.",
            },
            "intent": {
                "type": "string",
                "description": "The user's action intent: 'search', 'fetch', 'send', 'create', 'read', 'list', etc.",
            },
            "parameters": {
                "type": "object",
                "description": "Key-value parameters extracted for the action (e.g. query, summary, time_min, recipient).",
            },
        },
        "required": ["app_name", "intent"],
    }

    def _resolve_slug(self, app_name: str, intent: str) -> str:
        """Resolve app and intent to a Composio action slug."""
        app_clean = app_name.lower().replace("_", "").replace(" ", "")
        intent_clean = intent.lower().replace("_", " ").split()[0] if intent else "search"

        # Direct match from mapping
        slug = INTENT_SLUG_MAP.get((app_clean, intent_clean))
        if slug:
            return slug

        # Fallback heuristic
        if "gmail" in app_clean:
            return "GMAIL_SEND_EMAIL" if "send" in intent.lower() else "GMAIL_FETCH_EMAILS"
        if "calendar" in app_clean:
            return "GOOGLECALENDAR_CREATE_EVENT" if "create" in intent.lower() else "GOOGLECALENDAR_FIND_EVENT"
        if "sheet" in app_clean:
            return "GOOGLESHEETS_APPEND_VALUES" if "append" in intent.lower() else "GOOGLESHEETS_BATCH_GET"
        if "drive" in app_clean:
            return "GOOGLEDRIVE_SEARCH_FILES"
        if "doc" in app_clean:
            return "GOOGLEDOCS_CREATE_DOCUMENT"
        if "outlook" in app_clean:
            return "OUTLOOK_SEND_MAIL" if "send" in intent.lower() else "OUTLOOK_GET_EMAILS"
        if "serp" in app_clean:
            return "SERPAPI_SEARCH"
        if "perplexity" in app_clean:
            return "PERPLEXITYAI_PERPLEXITY_AI_SEARCH"

        return f"{app_clean.upper()}_{intent_clean.upper()}"

    async def execute(
        self,
        app_name: str,
        intent: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", "default_user")
        confirmed = kwargs.get("confirmed", False)
        intent_first_word = intent.lower().replace("_", " ").split()[0] if intent else ""

        # Enforce execution boundary safety for dynamic write operations
        if intent_first_word in WRITE_INTENTS and not confirmed:
            logger.info(f"Dynamic App Action write intent '{intent}' requires verbal confirmation.")
            return {
                "success": False,
                "requires_confirmation": True,
                "app": app_name,
                "intent": intent,
                "parameters": parameters,
                "spoken_summary": f"I am ready to {intent} on {app_name}. Would you like me to proceed?",
            }

        slug = self._resolve_slug(app_name, intent)
        params = parameters or {}

        logger.info(f"Dynamic App Action: app={app_name}, intent={intent} -> slug={slug}, user_id={user_id}")
        res = await composio_gateway.execute_action(slug, params, entity_id=user_id)

        if res.get("success"):
            return {
                "success": True,
                "app": app_name,
                "action": slug,
                "spoken_summary": f"I executed {intent} on {app_name} successfully.",
                "data": res.get("data", res),
            }

        return {
            "success": False,
            "app": app_name,
            "action": slug,
            "error": res.get("error", "Action failed"),
            "spoken_summary": f"I had trouble executing {intent} on {app_name}.",
        }
