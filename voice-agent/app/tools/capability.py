"""Capability Resolver and Provider Disambiguation Engine.

Resolves model-facing semantic requests (e.g. search_emails, create_calendar_event)
to concrete connected provider toolkits (Gmail vs. Outlook; Google Calendar vs. Outlook)
based on active user connections, explicit requests, and disambiguation policies.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.integrations.composio.client import composio_gateway

logger = logging.getLogger(__name__)


def canonical_app_slug(app: str) -> str:
    """Normalize the toolkit spellings returned by Composio into stable IDs."""
    normalized = (app or "").upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "GOOGLE_CALENDAR": "GOOGLECALENDAR",
        "GOOGLE_CAL": "GOOGLECALENDAR",
        "MICROSOFT_OUTLOOK": "OUTLOOK",
        "OFFICE_365": "OUTLOOK",
    }
    return aliases.get(normalized, normalized)


def is_account_active(status: str) -> bool:
    """Canonical check for whether a Composio connected account is usable.

    The Composio SDK returns different status strings depending on provider and
    SDK version: "ACTIVE", "CONNECTED", or sometimes empty (default active).
    This single function is the source of truth used everywhere.
    """
    normalized = (status or "").upper().strip()
    return normalized in ("ACTIVE", "CONNECTED", "")


class CapabilityResolver:
    """Resolves provider toolkits for user capabilities dynamically."""

    async def get_user_connected_apps(self, user_id: str) -> List[str]:
        """Fetch list of uppercase connected app slugs for a user entity."""
        accounts = await composio_gateway.get_connected_accounts(entity_id=user_id)
        connected = []
        for acc in accounts:
            if is_account_active(acc.get("status", "")) and acc.get("is_active", True):
                app_slug = canonical_app_slug(acc.get("app", ""))
                if app_slug:
                    connected.append(app_slug)
        return connected

    async def resolve_email_provider(
        self,
        user_id: str,
        requested_provider: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Resolve email provider ('gmail' or 'outlook') based on connected accounts.

        Returns:
            (resolved_provider, error_or_disambiguation_dict)
        """
        connected_apps = await self.get_user_connected_apps(user_id)
        has_gmail = "GMAIL" in connected_apps
        has_outlook = "OUTLOOK" in connected_apps

        # 1. User explicitly requested a provider
        if requested_provider:
            req = requested_provider.lower().strip()
            if req in ("gmail", "google"):
                if has_gmail:
                    return "gmail", None
                return None, self._unavailable("Gmail", "email")
            elif req in ("outlook", "microsoft", "office365"):
                if has_outlook:
                    return "outlook", None
                return None, self._unavailable("Outlook", "email")

        # 2. Only Gmail connected
        if has_gmail and not has_outlook:
            return "gmail", None

        # 3. Only Outlook connected
        if has_outlook and not has_gmail:
            return "outlook", None

        # 4. Both connected and no explicit preference -> Disambiguation required
        if has_gmail and has_outlook:
            return None, {
                "success": False,
                "requires_disambiguation": True,
                "capability": "email",
                "available_providers": ["gmail", "outlook"],
                "spoken_summary": "You have both Gmail and Outlook connected. Which email account would you like me to use?",
            }

        # 5. Connection status is a precondition, never a provider default.
        return None, self._unavailable("an email account", "email")

    async def resolve_calendar_provider(
        self,
        user_id: str,
        requested_provider: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Resolve calendar provider ('google' or 'outlook') based on connected accounts.

        Returns:
            (resolved_provider, error_or_disambiguation_dict)
        """
        connected_apps = await self.get_user_connected_apps(user_id)
        has_google = "GOOGLECALENDAR" in connected_apps
        has_outlook = "OUTLOOK" in connected_apps

        # 1. User explicitly requested a provider
        if requested_provider:
            req = requested_provider.lower().strip()
            if req in ("google", "googlecalendar", "gmail"):
                if has_google:
                    return "google", None
                return None, self._unavailable("Google Calendar", "calendar")
            elif req in ("outlook", "microsoft", "office365"):
                if has_outlook:
                    return "outlook", None
                return None, self._unavailable("Outlook", "calendar")

        # 2. Only Google Calendar connected
        if has_google and not has_outlook:
            return "google", None

        # 3. Only Outlook connected
        if has_outlook and not has_google:
            return "outlook", None

        # 4. Both connected and no explicit preference -> Disambiguation required
        if has_google and has_outlook:
            return None, {
                "success": False,
                "requires_disambiguation": True,
                "capability": "calendar",
                "available_providers": ["google", "outlook"],
                "spoken_summary": "You have both Google Calendar and Outlook connected. Which calendar would you like me to use?",
            }

        # 5. Connection status is a precondition, never a provider default.
        return None, self._unavailable("a calendar", "calendar")

    @staticmethod
    def _unavailable(provider: str, capability: str) -> Dict[str, Any]:
        return {
            "success": False,
            "status": "connection_unavailable",
            "capability": capability,
            "error": f"{provider} is not connected for this user.",
            "spoken_summary": f"I can't access {provider} because it isn't connected to your account.",
        }


capability_resolver = CapabilityResolver()
