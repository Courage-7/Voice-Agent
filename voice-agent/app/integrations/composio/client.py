"""Composio integration client, OAuth connection manager, and action executor."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _field(value: Any, name: str, default: Any = None) -> Any:
    """Read SDK models and JSON dictionaries without mistaking dict.items for data."""
    return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)

# Baseline project apps fallback matching active user Composio auth configs
BASELINE_PROJECT_APPS = [
    {"name": "GMAIL", "slug": "gmail", "display_name": "Gmail", "capability": "communication", "categories": ["communication", "workspace"], "description": "Google Workspace Gmail email service with thread search and drafting.", "logo_url": "https://logos.composio.dev/api/gmail"},
    {"name": "GOOGLECALENDAR", "slug": "googlecalendar", "display_name": "Google Calendar", "capability": "productivity", "categories": ["productivity", "workspace"], "description": "Google Calendar scheduling, event reminders, and availability.", "logo_url": "https://logos.composio.dev/api/googlecalendar"},
    {"name": "GOOGLEDOCS", "slug": "googledocs", "display_name": "Google Docs", "capability": "productivity", "categories": ["productivity", "workspace"], "description": "Cloud-based word processor for creating and managing documentation.", "logo_url": "https://logos.composio.dev/api/googledocs"},
    {"name": "GOOGLESHEETS", "slug": "googlesheets", "display_name": "Google Sheets", "capability": "productivity", "categories": ["productivity", "workspace"], "description": "Spreadsheet platform for tabular records, data analysis, and calculations.", "logo_url": "https://logos.composio.dev/api/googlesheets"},
    {"name": "GOOGLEDRIVE", "slug": "googledrive", "display_name": "Google Drive", "capability": "productivity", "categories": ["productivity", "workspace"], "description": "Cloud storage to search, retrieve, and index workspace documents.", "logo_url": "https://logos.composio.dev/api/googledrive"},
    {"name": "OUTLOOK", "slug": "outlook", "display_name": "Microsoft Outlook 365", "capability": "communication", "categories": ["communication", "workspace"], "description": "Microsoft Outlook email, calendar, and contacts synchronization.", "logo_url": "https://logos.composio.dev/api/outlook"},
    {"name": "NOTION", "slug": "notion", "display_name": "Notion", "capability": "productivity", "categories": ["productivity", "workspace"], "description": "Unified workspace for notes, knowledge bases, wikis, and sprint tasks.", "logo_url": "https://logos.composio.dev/api/notion"},
    {"name": "SERPAPI", "slug": "serpapi", "display_name": "SerpApi (Google Search)", "capability": "search", "categories": ["search", "research"], "description": "Real-time Google search with structured results and web snippets.", "logo_url": "https://logos.composio.dev/api/serpapi"},
    {"name": "PERPLEXITYAI", "slug": "perplexityai", "display_name": "Perplexity AI", "capability": "search", "categories": ["search", "research"], "description": "Conversational AI and web research engine providing factual citations.", "logo_url": "https://logos.composio.dev/api/perplexityai"},
    {"name": "TAVILY", "slug": "tavily", "display_name": "Tavily Search", "capability": "search", "categories": ["search", "research"], "description": "AI-optimized search and data retrieval engine for high-accuracy answers.", "logo_url": "https://logos.composio.dev/api/tavily"},
    {"name": "VAPI", "slug": "vapi", "display_name": "Vapi Voice AI", "capability": "developer", "categories": ["developer", "voice"], "description": "Voice AI platform enabling telephone calls, assistants, and voice agents.", "logo_url": "https://logos.composio.dev/api/vapi"},
    {"name": "I_LOVE_PDF", "slug": "i_love_pdf", "display_name": "iLovePDF", "capability": "productivity", "categories": ["productivity", "workspace"], "description": "PDF processing APIs for converting, compressing, and managing PDFs.", "logo_url": "https://logos.composio.dev/api/ilovepdf"},
    {"name": "MICROSOFT_TEAMS", "slug": "microsoft_teams", "display_name": "Microsoft Teams", "capability": "communication", "categories": ["communication", "collaboration"], "description": "Enterprise collaboration platform for chats, channels, and team meetings.", "logo_url": "https://logos.composio.dev/api/microsoftteams"},
    {"name": "WHATSAPP", "slug": "whatsapp", "display_name": "WhatsApp", "capability": "communication", "categories": ["communication", "messaging"], "description": "Direct messaging, customer alerts, and real-time chat notifications.", "logo_url": "https://logos.composio.dev/api/whatsapp"},
    {"name": "TELEGRAM", "slug": "telegram", "display_name": "Telegram", "capability": "communication", "categories": ["communication", "messaging"], "description": "Cloud-based messaging, bot integration, and broadcast channels.", "logo_url": "https://logos.composio.dev/api/telegram"},
    {"name": "LINKEDIN", "slug": "linkedin", "display_name": "LinkedIn", "capability": "communication", "categories": ["communication", "social"], "description": "Professional networking platform for posts, profiles, and business updates.", "logo_url": "https://logos.composio.dev/api/linkedin"},
    {"name": "NEON", "slug": "neon", "display_name": "Neon Serverless PostgreSQL", "capability": "database", "categories": ["database", "developer"], "description": "Serverless Postgres with autoscaling, database branching, and instant provisioning.", "logo_url": "https://logos.composio.dev/api/neon"},
]


class ComposioGateway:
    """Gateway to manage Composio OAuth connections and execute actions."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.composio_api_key
        self._client = None
        self._initialization_error: Optional[str] = None
        self._auth_configs_cache: Dict[str, str] = {}
        self._connected_accounts_cache: Dict[str, tuple[float, List[Dict[str, Any]]]] = {}
        self._supported_apps_cache: Optional[List[Dict[str, Any]]] = None
        self._user_sessions: Dict[str, Any] = {}
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Lazily initialize Composio Client if API key is present."""
        if settings.demo_mode:
            return
        if not self.api_key:
            logger.warning("COMPOSIO_API_KEY is not configured. Composio running in fallback mode.")
            return

        try:
            from composio import Composio
            client = Composio(api_key=self.api_key)
            if not callable(getattr(getattr(client, "auth_configs", None), "list", None)) or not callable(
                getattr(getattr(client, "connected_accounts", None), "link", None)
            ):
                raise RuntimeError("Installed Composio SDK does not support auth configs and Connect Links")
            self._client = client
            logger.info("Composio client initialized successfully.")
        except Exception:
            logger.exception("Failed to initialize Composio client")
            self._client = None
            self._initialization_error = (
                "The Composio SDK could not initialize. Repair the backend dependencies "
                "(remove legacy composio-core and reinstall composio), then restart the backend."
            )

    def _list_auth_configs_sync(self) -> List[Any]:
        """Read all enabled project configs; a lookup failure is not an empty project."""
        configs: List[Any] = []
        query: Dict[str, Any] = {"limit": 100, "show_disabled": False}
        seen_cursors: set[str] = set()
        try:
            while True:
                page = self._client.auth_configs.list(**query)
                items = page if isinstance(page, (list, tuple)) else _field(page, "items", _field(page, "data", []))
                if not isinstance(items, (list, tuple)):
                    raise ValueError("Unexpected Composio auth config response")
                configs.extend(item for item in items if _field(item, "status", "ENABLED") == "ENABLED")
                cursor = _field(page, "next_cursor")
                if not cursor:
                    return configs
                if not isinstance(cursor, str) or cursor in seen_cursors:
                    raise ValueError("Invalid Composio auth config pagination")
                seen_cursors.add(cursor)
                query["cursor"] = cursor
        except Exception as exc:
            logger.error("Composio auth config lookup failed (%s)", type(exc).__name__)
            raise RuntimeError(
                "Could not retrieve authentication configurations from Composio. "
                "Check the backend Composio SDK, project API key, and network connection."
            ) from exc

    def get_supported_apps(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """Return strictly the apps configured in the user's Composio project."""
        if self._initialization_error:
            raise RuntimeError(self._initialization_error)
        if not self._client or settings.demo_mode:
            return BASELINE_PROJECT_APPS

        if self._supported_apps_cache is not None and not refresh:
            return self._supported_apps_cache

        try:
            items = self._list_auth_configs_sync()

            discovered_apps: List[Dict[str, Any]] = []
            seen_slugs: set[str] = set()

            for ac in items:
                tk = _field(ac, "toolkit")
                raw_slug = (_field(tk, "slug", "") or _field(ac, "toolkit_slug", "") or "").lower()
                if not raw_slug or not _field(ac, "id") or raw_slug in seen_slugs:
                    continue
                seen_slugs.add(raw_slug)

                meta = _field(tk, "meta")
                tk_name = _field(tk, "name", "") or raw_slug.replace("_", " ").title()
                desc = (
                    _field(meta, "description", "")
                    or _field(tk, "description", "")
                    or f"{tk_name} integration configured in your Composio project."
                )
                logo = (
                    _field(meta, "logo", "")
                    or _field(tk, "logo", "")
                    or f"https://logos.composio.dev/api/{raw_slug.replace('_', '')}"
                )

                raw_lower = raw_slug.lower()
                if raw_lower in ("gmail", "outlook", "whatsapp", "telegram", "microsoft_teams", "linkedin"):
                    cap = "communication"
                elif raw_lower in ("serpapi", "perplexityai", "tavily"):
                    cap = "search"
                elif raw_lower in ("neon", "postgresql"):
                    cap = "database"
                elif raw_lower in ("vapi", "github", "linear"):
                    cap = "developer"
                else:
                    cap = "productivity"

                discovered_apps.append({
                    "name": raw_slug.upper(),
                    "slug": raw_slug,
                    "display_name": tk_name,
                    "capability": cap,
                    "description": desc,
                    "logo_url": logo,
                    "auth_config_id": _field(ac, "id"),
                    "auth_scheme": _field(ac, "auth_scheme", ""),
                })

            self._supported_apps_cache = discovered_apps
            return discovered_apps
        except Exception:
            # Do not make a provider failure look like 17 configured, linkable apps.
            logger.error("Cannot load the Composio connector catalog")
            raise

    async def get_or_create_user_session(
        self,
        user_id: str,
        toolkits: Optional[List[str]] = None,
    ) -> Optional[Any]:
        """Get or initialize a user-scoped Composio Session."""
        if not self._client or not hasattr(self._client, "sessions"):
            return None

        if user_id in self._user_sessions:
            return self._user_sessions[user_id]

        try:
            allowed_toolkits = toolkits or [
                app.get("slug", app["name"].lower()) for app in self.get_supported_apps()
            ]
            session = await asyncio.to_thread(
                self._client.sessions.create,
                user_id=user_id,
                toolkits=allowed_toolkits,
            )
            self._user_sessions[user_id] = session
            logger.info(f"Initialized Composio Session for user '{user_id}' with toolkits: {allowed_toolkits}")
            return session
        except Exception:
            logger.exception(f"Failed to create Composio Session for user '{user_id}'")
            return None

    async def discover_user_tools(self, user_id: str) -> List[Dict[str, Any]]:
        """Dynamically discover available tools for a user from their Composio Session."""
        session = await self.get_or_create_user_session(user_id)
        if not session or not hasattr(session, "tools"):
            return []

        try:
            tools = await asyncio.to_thread(session.tools)
            discovered = []
            for t in tools:
                slug = getattr(t, "slug", getattr(t, "name", ""))
                desc = getattr(t, "description", "")
                params = getattr(t, "parameters", {})
                discovered.append({"slug": slug, "description": desc, "parameters": params})
            return discovered
        except Exception:
            logger.exception(f"Failed to discover tools for user '{user_id}'")
            return []

    def _get_auth_config_id_sync(self, app_name: str) -> Optional[str]:
        """Resolve active auth config ID for an app slug within the Composio project."""
        if not self._client:
            return None

        clean = app_name.lower().strip()
        stripped = clean.replace("_", "").replace("-", "")

        # Refresh at connect time so deleted/disabled configs cannot remain cached.
        configs: Dict[str, str] = {}
        for ac in self._list_auth_configs_sync():
            tk = _field(ac, "toolkit")
            slug = (_field(tk, "slug", "") or _field(ac, "toolkit_slug", "") or "").lower()
            ac_id = _field(ac, "id", "")
            if slug and ac_id:
                # Match the catalog's first enabled config when a toolkit has duplicates.
                configs.setdefault(slug, ac_id)
                configs.setdefault(slug.replace("_", "").replace("-", ""), ac_id)
        self._auth_configs_cache = configs
        return configs.get(clean) or configs.get(stripped)

    async def initiate_connection(
        self,
        app_name: str,
        entity_id: str = "default_user",
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initiate OAuth connection flow and return redirect authorization URL."""
        if not self._client:
            return {
                "success": False,
                "status": "unavailable",
                "app": app_name.upper(),
                "entity_id": entity_id,
                "error": self._initialization_error or "Composio is unavailable. No authorization link was created.",
            }

        try:
            auth_config_id = await asyncio.to_thread(self._get_auth_config_id_sync, app_name)
            if not auth_config_id:
                return {
                    "success": False,
                    "app": app_name.upper(),
                    "error": f"No active auth config found in Composio project for app '{app_name}'.",
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
            redirect_url = _field(connection_request, "redirect_url") or _field(connection_request, "redirectUrl") or _field(connection_request, "url")
            conn_id = _field(connection_request, "connected_account_id") or _field(connection_request, "id", "")
            if not isinstance(redirect_url, str) or not redirect_url.startswith("https://"):
                raise RuntimeError("Composio did not return a valid authorization link. Please retry connecting.")
            # The account list may contain a pre-connect empty result.  OAuth
            # completion is polled by the client, so make the very next read
            # ask Composio instead of serving that stale result for up to 60s.
            self.invalidate_connected_accounts(entity_id)
            return {
                "success": True,
                "app": app_name.upper(),
                "entity_id": entity_id,
                "redirect_url": str(redirect_url),
                "auth_url": str(redirect_url),
                "connection_id": str(conn_id),
            }
        except Exception as e:
            logger.exception(f"Failed to initiate Composio OAuth for {app_name}")
            return {
                "success": False,
                "app": app_name.upper(),
                "error": str(e),
            }

    def invalidate_connected_accounts(self, entity_id: str) -> None:
        """Discard one user's cached OAuth account resolution.

        Connection state is a security and execution precondition, not a
        durable application setting.  Call this around OAuth changes so a
        successful connection is usable immediately by the action runner.
        """
        self._connected_accounts_cache.pop(entity_id, None)

    async def get_connected_accounts(self, entity_id: str = "default_user", force_refresh: bool = False) -> List[Dict[str, Any]]:
        """List active connected accounts and OAuth statuses for a user entity with 60s TTL cache."""
        if not self._client:
            return []

        # Return cached list if fresh (< 60s) to prevent session startup delay
        now = time.time()
        if not force_refresh and entity_id in self._connected_accounts_cache:
            ts, cached_data = self._connected_accounts_cache[entity_id]
            if now - ts < 60.0:
                return cached_data

        try:
            # Enforce 1.2s timeout to prevent session startup lag
            res = await asyncio.wait_for(
                asyncio.to_thread(
                    self._client.connected_accounts.list,
                    user_ids=[entity_id],
                ),
                timeout=1.2,
            )
            accounts = _field(res, "items", _field(res, "data", [])) or []
            connected_list = []
            for acc in accounts:
                tk = _field(acc, "toolkit")
                slug = _field(tk, "slug", "") if tk else ""
                if not slug:
                    slug = _field(acc, "toolkit_slug", "") or _field(acc, "app_name", "")

                raw_status = _field(acc, "status")
                status = str(raw_status or "ACTIVE").upper()
                is_active = status in ("ACTIVE", "CONNECTED")
                conn_id = str(_field(acc, "id", ""))
                connected_list.append({
                    "app": slug.upper(),
                    "app_key": slug.upper(),
                    "status": status,
                    "is_active": is_active,
                    "id": conn_id,
                    "connection_id": conn_id,
                })
            self._connected_accounts_cache[entity_id] = (now, connected_list)
            return connected_list
        except asyncio.TimeoutError as exc:
            logger.warning("Timed out fetching connected accounts for %s", entity_id)
            raise RuntimeError("Composio connected-account resolution timed out.") from exc
        except Exception as exc:
            logger.exception("Failed to fetch connected accounts for %s", entity_id)
            raise RuntimeError("Composio connected-account resolution failed.") from exc

    async def disconnect_account(self, connection_id: str, entity_id: str) -> Dict[str, Any]:
        """Revoke an integrated account only when it belongs to the verified entity."""
        if not self._client:
            return {"success": False, "status": "unavailable", "error": "Composio is unavailable. No connection was removed."}

        try:
            accounts = await self.get_connected_accounts(entity_id=entity_id, force_refresh=True)
            owned_ids = {str(account.get("connection_id") or account.get("id")) for account in accounts}
            if str(connection_id) not in owned_ids:
                return {
                    "success": False,
                    "status": "authorization_error",
                    "error": "The connection does not belong to the authenticated user.",
                }

            if hasattr(self._client.connected_accounts, "delete"):
                try:
                    await asyncio.to_thread(self._client.connected_accounts.delete, connection_id)
                except TypeError:
                    await asyncio.to_thread(self._client.connected_accounts.delete, connected_account_id=connection_id)
            self.invalidate_connected_accounts(entity_id)
            return {"success": True, "message": f"Connection '{connection_id}' successfully removed."}
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                self.invalidate_connected_accounts(entity_id)
                return {"success": True, "message": f"Connection '{connection_id}' already removed or not found."}
            logger.exception(f"Failed to disconnect account {connection_id}")
            return {"success": False, "error": str(e)}

    async def execute_action(
        self,
        action_name: str,
        params: Dict[str, Any],
        entity_id: str = "default_user",
    ) -> Dict[str, Any]:
        """Execute an action through the authenticated user's Composio Session.

        Direct tool execution is deliberately unsupported: a session is the
        boundary that owns user identity, selected accounts, and the audit log.
        """
        logger.info(f"Executing Composio action '{action_name}' for entity '{entity_id}' with params: {params}")

        if not self._client:
            # Missing configuration must produce unavailable/failure, never fabricated success (F04)
            return {
                "success": False,
                "status": "unavailable",
                "error": "Composio integration gateway is unconfigured.",
                "spoken_summary": f"I cannot execute {action_name} because the integration service is not configured.",
                "data": {"successful": False, "error": "Composio client not initialized"},
            }

        try:
            session = await self.get_or_create_user_session(entity_id)
            execute = getattr(session, "execute", None) if session else None
            if not callable(execute):
                return {
                    "success": False,
                    "status": "unavailable",
                    "error": "Composio user session execution is unavailable.",
                    "spoken_summary": "I cannot execute this integration action because the authenticated integration session is unavailable.",
                }

            result = await asyncio.to_thread(execute, action_name, arguments=params)
            data = _field(result, "data", result)
            if not isinstance(data, dict):
                data = {"response": str(data)}

            # ``result.error`` is Composio's authoritative execution result;
            # some successful SDK responses do not expose a ``success`` flag.
            # An explicit false success field remains a failure.
            provider_error = _field(result, "error") or data.get("error")
            explicit_success = _field(result, "success")
            data_success = data.get("successful", data.get("success"))
            if provider_error or explicit_success is False or data_success is False:
                detail = str(provider_error or "Composio did not confirm that the action completed.")
                logger.warning("Action '%s' failed through the user session: %s", action_name, detail)
                return {
                    "success": False,
                    "status": "failure",
                    "error": detail,
                    "spoken_summary": f"Execution of {action_name} failed: {detail}",
                    "data": data,
                }

            logger.info(f"Action '{action_name}' executed successfully.")
            return {
                "success": True,
                "status": "success",
                "data": data,
                "provider_log_id": _field(result, "log_id") or _field(result, "logId"),
                "spoken_summary": f"Successfully completed {action_name}.",
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
            logger.exception(f"Exception executing action '{action_name}'")
            return {
                "success": False,
                "status": "error",
                "error": str(e),
                "spoken_summary": f"An error occurred while executing {action_name}: {str(e)[:100]}",
                "data": {"error": str(e)},
            }

    async def resolve_skill_steps(
        self,
        goal: str,
        entity_id: str = "default_user",
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Resolve a high-level goal into multi-step tool calls based on user's active Composio connections."""
        context = context or {}
        try:
            connected_accounts = await self.get_connected_accounts(entity_id=entity_id)
            connected_apps = {acc.get("app", "").upper() for acc in connected_accounts if acc.get("status") == "ACTIVE"}
            goal_lower = goal.lower()
            steps: List[Dict[str, Any]] = []

            # Skill 1: Research & Document Compilation (Tavily/Perplexity/SerpApi -> Google Docs)
            if ("research" in goal_lower or "search" in goal_lower) and ("doc" in goal_lower or "document" in goal_lower or "notes" in goal_lower):
                query = context.get("query") or context.get("prompt") or goal
                use_tavily = "TAVILY" in connected_apps
                use_perplexity = "PERPLEXITYAI" in connected_apps
                if use_tavily:
                    research_tool = "tavily_search"
                    research_args = {"query": query}
                elif use_perplexity:
                    research_tool = "perplexity_ai_research"
                    research_args = {"prompt": query}
                else:
                    research_tool = "web_search_serpapi"
                    research_args = {"query": query}

                steps.append({
                    "description": f"Perform online research on '{query[:60]}'",
                    "tool_name": research_tool,
                    "arguments": research_args,
                })
                steps.append({
                    "description": "Compile research findings into a Google Doc",
                    "tool_name": "manage_google_doc",
                    "arguments": {
                        "title": context.get("title") or f"Research: {query[:40]}",
                        "content": context.get("content", "Synthesized research findings..."),
                    },
                })
                return steps

            # Skill 2: Inbox Triage & Spreadsheet Logging (Email -> Google Sheets)
            if "email" in goal_lower and ("sheet" in goal_lower or "spreadsheet" in goal_lower or "log" in goal_lower):
                steps.append({
                    "description": "Search inbox for relevant messages",
                    "tool_name": "search_emails",
                    "arguments": {"query": context.get("query", "is:unread")},
                })
                steps.append({
                    "description": "Log email records into Google Sheet",
                    "tool_name": "manage_google_sheet",
                    "arguments": {
                        "spreadsheet_id": context.get("spreadsheet_id", "active_sheet"),
                        "action": "append",
                        "values": ["Subject", "Sender", "Date"],
                    },
                })
                return steps

            # Skill 3: Calendar Availability Check & Scheduling
            if ("schedule" in goal_lower or "calendar" in goal_lower or "meeting" in goal_lower) and ("check" in goal_lower or "find" in goal_lower or "slot" in goal_lower or "free" in goal_lower):
                steps.append({
                    "description": "Check upcoming calendar availability",
                    "tool_name": "list_calendar_events",
                    "arguments": {"max_events": 5},
                })
                if "create" in goal_lower or "schedule" in goal_lower or "book" in goal_lower:
                    steps.append({
                        "description": "Schedule calendar meeting",
                        "tool_name": "create_calendar_event",
                        "arguments": {
                            "title": context.get("title", "Follow-up Meeting"),
                            "start_time": context.get("start_time", "tomorrow at 10 AM"),
                        },
                    })
                return steps

            return []
        except Exception:
            logger.exception(f"Failed to dynamically resolve Composio skills for goal '{goal}'")
            return []


composio_gateway = ComposioGateway()
