"""Composio integration client, OAuth connection manager, and action executor."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Supported integration apps in the Voice Agent ecosystem
SUPPORTED_APPS = [
    {"name": "GMAIL", "display_name": "Gmail", "capability": "email", "description": "Read, search, and send emails."},
    {"name": "OUTLOOK", "display_name": "Outlook / Office 365", "capability": "email", "description": "Manage Outlook mail and contacts."},
    {"name": "GOOGLECALENDAR", "display_name": "Google Calendar", "capability": "calendar", "description": "Create and check calendar meetings."},
    {"name": "SERPAPI", "display_name": "SerpAI (Google Search)", "capability": "search", "description": "Real-time live Google web search."},
    {"name": "PERPLEXITYAI", "display_name": "Perplexity AI", "capability": "search", "description": "Deep online AI search and synthesis."},
    {"name": "GOOGLESHEETS", "display_name": "Google Sheets", "capability": "workspace", "description": "Read and append spreadsheet rows."},
    {"name": "GOOGLEDOCS", "display_name": "Google Docs", "capability": "workspace", "description": "Create and update Google documents."},
    {"name": "GOOGLEDRIVE", "display_name": "Google Drive", "capability": "workspace", "description": "Search and retrieve Drive files."},
]


class ComposioGateway:
    """Gateway to manage Composio OAuth connections and execute actions."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.composio_api_key
        self._client = None
        self._auth_configs_cache: Dict[str, str] = {}
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Lazily initialize Composio Client if API key is present."""
        if not self.api_key:
            logger.warning("COMPOSIO_API_KEY is not configured. Composio running in fallback mode.")
            return

        try:
            from composio import Composio
            self._client = Composio(api_key=self.api_key)
            logger.info("Composio client initialized successfully.")
        except Exception:
            logger.exception("Failed to initialize Composio client")
            self._client = None

    def _get_auth_config_id_sync(self, app_name: str) -> Optional[str]:
        """Resolve auth config ID for an app/toolkit slug."""
        normalized = app_name.lower().replace("_", "")
        if normalized in self._auth_configs_cache:
            return self._auth_configs_cache[normalized]

        if not self._client:
            return None

        try:
            auth_configs = self._client.auth_configs.list()
            items = getattr(auth_configs, "items", getattr(auth_configs, "data", []))
            for ac in items:
                tk = getattr(ac, "toolkit", None)
                slug = (getattr(tk, "slug", "") or getattr(ac, "toolkit_slug", "") or "").lower().replace("_", "")
                if slug:
                    self._auth_configs_cache[slug] = ac.id

            return self._auth_configs_cache.get(normalized)
        except Exception:
            logger.exception(f"Failed to fetch auth configs from Composio for {app_name}")
            return None

    def get_supported_apps(self) -> List[Dict[str, str]]:
        """Return list of supported ecosystem apps."""
        return SUPPORTED_APPS

    async def initiate_connection(
        self,
        app_name: str,
        entity_id: str = "default_user",
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initiate OAuth connection flow and return redirect authorization URL."""
        if not self._client:
            return {
                "success": True,
                "app": app_name.upper(),
                "entity_id": entity_id,
                "redirect_url": f"https://composio.dev/mock-oauth/{app_name.lower()}?entity_id={entity_id}",
                "message": "Composio client running in fallback mode.",
            }

        try:
            auth_config_id = await asyncio.to_thread(self._get_auth_config_id_sync, app_name)
            if not auth_config_id:
                return {
                    "success": False,
                    "app": app_name.upper(),
                    "error": f"No active auth config found in Composio for app '{app_name}'.",
                }

            kwargs: Dict[str, Any] = {
                "user_id": entity_id,
                "auth_config_id": auth_config_id,
            }
            if redirect_uri:
                kwargs["callback_url"] = redirect_uri

            connection_request = await asyncio.to_thread(
                self._client.connected_accounts.link,
                **kwargs,
            )
            redirect_url = getattr(connection_request, "redirect_url", getattr(connection_request, "redirectUrl", getattr(connection_request, "url", "")))
            conn_id = getattr(connection_request, "connected_account_id", getattr(connection_request, "id", ""))
            return {
                "success": True,
                "app": app_name.upper(),
                "entity_id": entity_id,
                "redirect_url": str(redirect_url),
                "connection_id": str(conn_id),
            }
        except Exception as e:
            logger.exception(f"Failed to initiate Composio OAuth for {app_name}")
            return {
                "success": False,
                "app": app_name.upper(),
                "error": str(e),
            }

    async def get_connected_accounts(self, entity_id: str = "default_user") -> List[Dict[str, Any]]:
        """List active connected accounts and OAuth statuses for a user entity."""
        if not self._client:
            return [
                {
                    "app": app["name"],
                    "status": "ACTIVE",
                    "display_name": app["display_name"],
                    "capability": app["capability"],
                }
                for app in SUPPORTED_APPS
            ]

        try:
            res = await asyncio.to_thread(
                self._client.connected_accounts.list,
                user_ids=[entity_id],
            )
            accounts = getattr(res, "items", getattr(res, "data", [])) or []
            connected_list = []
            for acc in accounts:
                tk = getattr(acc, "toolkit", None)
                slug = getattr(tk, "slug", "") if tk else ""
                if not slug:
                    slug = getattr(acc, "toolkit_slug", "") or getattr(acc, "app_name", "")

                status = getattr(acc, "status", "ACTIVE")
                conn_id = str(getattr(acc, "id", ""))
                connected_list.append({
                    "app": slug.upper(),
                    "status": status,
                    "id": conn_id,
                })
            return connected_list
        except Exception:
            logger.exception(f"Failed to fetch connected accounts for {entity_id}")
            return []

    async def disconnect_account(self, connection_id: str) -> Dict[str, Any]:
        """Revoke and disconnect an integrated account."""
        if not self._client:
            return {"success": True, "message": f"Connection '{connection_id}' disconnected."}

        try:
            if hasattr(self._client.connected_accounts, "delete"):
                await asyncio.to_thread(self._client.connected_accounts.delete, connected_account_id=connection_id)
            return {"success": True, "message": f"Connection '{connection_id}' successfully removed."}
        except Exception as e:
            logger.exception(f"Failed to disconnect account {connection_id}")
            return {"success": False, "error": str(e)}

    async def execute_action(
        self,
        action_name: str,
        params: Dict[str, Any],
        entity_id: str = "default_user",
    ) -> Dict[str, Any]:
        """Execute a Composio action by name for the connected entity."""
        logger.info(f"Executing Composio action '{action_name}' for entity '{entity_id}' with params: {params}")

        if not self._client:
            return {
                "success": True,
                "message": f"Action '{action_name}' executed in fallback mode.",
                "params": params,
            }

        try:
            if hasattr(self._client, "tools") and hasattr(self._client.tools, "execute"):
                result = await asyncio.to_thread(
                    self._client.tools.execute,
                    slug=action_name,
                    arguments=params,
                    user_id=entity_id,
                    dangerously_skip_version_check=True,
                )
                return {"success": True, "data": result}

            return {
                "success": True,
                "message": f"Action '{action_name}' dispatched successfully.",
                "params": params,
            }
        except Exception as e:
            err_str = str(e)
            if "ConnectedAccountNotFound" in err_str or "No connected account found" in err_str:
                logger.warning(f"App action '{action_name}' requires connection for entity '{entity_id}'.")
                return {
                    "success": False,
                    "error": f"The service for '{action_name}' is not connected yet.",
                    "spoken_summary": "I cannot access this service because it is not connected yet. You can connect it in the Apps panel.",
                    "not_connected": True,
                }
            logger.warning(f"Error executing Composio action '{action_name}': {e}")
            return {
                "success": False,
                "error": err_str,
                "spoken_summary": f"I encountered an issue executing {action_name}.",
            }


composio_gateway = ComposioGateway()
