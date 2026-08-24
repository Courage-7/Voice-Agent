"""Capability Resolver and Provider Disambiguation Engine.

Resolves model-facing semantic requests (e.g. search_emails, create_calendar_event)
to concrete connected provider toolkits (Gmail vs. Outlook; Google Calendar vs. Outlook)
based on active user connections, explicit requests, and disambiguation policies.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.integrations.composio.client import composio_gateway

logger = logging.getLogger(__name__)


class CapabilityResolver:
    """Resolves provider toolkits for user capabilities dynamically."""

    async def get_user_connected_apps(self, user_id: str) -> List[str]:
        """Fetch list of uppercase connected app slugs for a user entity."""
        accounts = await composio_gateway.get_connected_accounts(entity_id=user_id)
        connected = []
        for acc in accounts:
            status = acc.get("status", "").upper()
            if status in ("ACTIVE", "CONNECTED", "INITIATED", ""):
                app_slug = acc.get("app", "").upper()
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
        has_gmail = "GMAIL" in connected_apps or "GOOGLE" in connected_apps
        has_outlook = "OUTLOOK" in connected_apps or "MICROSOFT" in connected_apps

        # 1. User explicitly requested a provider
        if requested_provider:
            req = requested_provider.lower().strip()
            if req in ("gmail", "google"):
                return "gmail", None
            elif req in ("outlook", "microsoft", "office365"):
                return "outlook", None

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

        # 5. Neither connected -> Fallback default with clear error summary
        return "gmail", None

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
        has_google = "GOOGLECALENDAR" in connected_apps or "GOOGLE" in connected_apps or "GMAIL" in connected_apps
        has_outlook = "OUTLOOK" in connected_apps or "MICROSOFT" in connected_apps

        # 1. User explicitly requested a provider
        if requested_provider:
            req = requested_provider.lower().strip()
            if req in ("google", "googlecalendar", "gmail"):
                return "google", None
            elif req in ("outlook", "microsoft", "office365"):
                return "outlook", None

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

        # 5. Neither connected -> Fallback default
        return "google", None


capability_resolver = CapabilityResolver()
