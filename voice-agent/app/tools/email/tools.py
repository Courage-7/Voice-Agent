"""Email tools: Gmail and Outlook integrations via Composio."""

from typing import Any, Dict, List
from app.integrations.composio.client import composio_gateway
from app.tools.base import BaseTool


def _extract_raw_messages(raw_data: Any) -> List[Dict[str, Any]]:
    """Extract message items safely from varying Composio response schemas."""
    if isinstance(raw_data, list):
        return [m for m in raw_data if isinstance(m, dict)]
    if not isinstance(raw_data, dict):
        return []

    inner = raw_data.get("data") or raw_data.get("response_data") or raw_data
    if isinstance(inner, dict):
        messages = inner.get("messages") or inner.get("items") or []
        return [m for m in messages if isinstance(m, dict)]
    if isinstance(inner, list):
        return [m for m in inner if isinstance(m, dict)]
    return []


def _format_compact_emails(raw_messages: List[Dict[str, Any]], max_results: int) -> List[Dict[str, str]]:
    """Format raw email messages into compact dictionaries for LLM speech."""
    compact_emails: List[Dict[str, str]] = []
    for msg in raw_messages[:max_results]:
        sender = str(msg.get("sender") or msg.get("from") or "Unknown")[:60]
        subject = str(msg.get("subject") or "No subject")[:100]
        preview = str(msg.get("preview") or msg.get("messageText") or msg.get("snippet") or "")[:120]
        compact_emails.append({"sender": sender, "subject": subject, "preview": preview})
    return compact_emails


class SendEmailTool(BaseTool):
    """Tool to send emails via Gmail or Outlook."""

    name = "send_email"
    description = "Send an email to one or more recipients using Gmail or Outlook."
    capability = "email"
    read_only = False
    requires_confirmation = True
    timeout_seconds = 15.0

    parameters = {
        "type": "object",
        "properties": {
            "recipient": {"type": "string", "description": "The recipient email address."},
            "subject": {"type": "string", "description": "The subject line of the email."},
            "body": {"type": "string", "description": "The body text of the email."},
            "provider": {
                "type": "string",
                "enum": ["gmail", "outlook"],
                "description": "Email provider to use. Defaults to gmail.",
            },
        },
        "required": ["recipient", "subject", "body"],
    }

    async def execute(
        self,
        recipient: str,
        subject: str,
        body: str,
        provider: str = "gmail",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", "default_user")
        action_name = "GMAIL_SEND_EMAIL" if provider.lower() == "gmail" else "OUTLOOK_SEND_MAIL"
        params = {"recipient_email": recipient, "subject": subject, "body": body}

        res = await composio_gateway.execute_action(action_name, params, entity_id=user_id)
        if res.get("success"):
            return {
                "success": True,
                "spoken_summary": f"I have sent the email to {recipient} with the subject '{subject}'.",
                "provider": provider,
                "data": res,
            }
        return {
            "success": False,
            "error": res.get("error", "Failed to send email"),
            "spoken_summary": f"I was unable to send the email to {recipient}.",
        }


class SearchEmailsTool(BaseTool):
    """Tool to search recent emails across Gmail or Outlook."""

    name = "search_emails"
    description = "Search through recent emails by query, sender, or subject."
    capability = "email"
    read_only = True
    requires_confirmation = False
    timeout_seconds = 10.0

    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search terms or keywords to locate."},
            "max_results": {"type": "integer", "description": "Maximum emails to retrieve. Default is 5."},
            "provider": {"type": "string", "enum": ["gmail", "outlook"], "description": "Provider to search."},
        },
        "required": ["query"],
    }

    async def execute(
        self,
        query: str,
        max_results: int = 5,
        provider: str = "gmail",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", "default_user")
        action_name = "GMAIL_FETCH_EMAILS" if provider.lower() == "gmail" else "OUTLOOK_GET_EMAILS"
        params = {"query": query, "max_results": max_results}

        res = await composio_gateway.execute_action(action_name, params, entity_id=user_id)
        if not res.get("success"):
            return {
                "success": False,
                "spoken_summary": res.get("spoken_summary", f"Unable to fetch emails for '{query}'."),
                "error": res.get("error", "Failed to fetch emails"),
            }

        raw_messages = _extract_raw_messages(res.get("data", {}))
        compact_emails = _format_compact_emails(raw_messages, max_results)

        count = len(compact_emails)
        if count == 1:
            summary = f"Found 1 email for '{query}'."
        elif count > 1:
            summary = f"Found {count} emails for '{query}'."
        else:
            summary = f"No emails found matching '{query}'."

        return {
            "success": True,
            "count": count,
            "spoken_summary": summary,
            "emails": compact_emails,
        }
