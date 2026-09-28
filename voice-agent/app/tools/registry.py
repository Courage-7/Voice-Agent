"""Central tool registry and policy engine for Voice AI Agent."""

import logging
from typing import Any, Dict, List, Optional

from app.tools.base import BaseTool
from app.tools.calendar.tools import CreateCalendarEventTool, ListCalendarEventsTool
from app.tools.email.tools import SearchEmailsTool, SendEmailTool
from app.tools.memory.save_memory import SaveMemoryTool
from app.tools.memory.search_memory import SearchMemoryTool
from app.tools.search.tools import PerplexityResearchTool, SerpApiSearchTool, TavilySearchTool
from app.tools.system.complex_task import RunComplexTaskTool
from app.tools.system.confirm_action import ConfirmActionTool
from app.tools.system.connected_apps import GetConnectedAppsTool
from app.tools.system.current_time import CurrentTimeTool
from app.tools.system.end_session import EndVoiceSessionTool
from app.tools.pending_actions import pending_action_store
from app.tools.workspace.dynamic_action import ExecuteAppActionTool
from app.tools.workspace.tools import GoogleDocsTool, GoogleDriveTool, GoogleSheetsTool
from app.tools.capability import canonical_app_slug

logger = logging.getLogger(__name__)



class ToolRegistry:
    """Registry managing tool lifecycle, discovery, capability routing, and confirmation policies."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name} (capability={tool.capability}, read_only={tool.read_only})")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by name, handling common model aliases."""
        tool = self._tools.get(name)
        if not tool:
            aliases = {
                "save_memory": "save_user_memory",
                "search_memory": "search_user_memory",
                "get_time": "get_current_time",
                "time": "get_current_time",
                "search_email": "search_emails",
                "send_emails": "send_email",
            }
            if name in aliases:
                tool = self._tools.get(aliases[name])
        return tool

    def get_all_tools(self) -> List[BaseTool]:
        """Get list of all registered tools."""
        return list(self._tools.values())

    def get_tools_by_capability(self, capability: str) -> List[BaseTool]:
        """Retrieve subset of tools matching a specific capability (e.g. 'email', 'calendar')."""
        return [t for t in self._tools.values() if t.capability.lower() == capability.lower()]

    def get_tools_for_capabilities(
        self,
        capabilities: Optional[List[str]] = None,
        connected_apps: Optional[List[str]] = None,
    ) -> List[BaseTool]:
        """Retrieve small relevant tool subset matching allowed capabilities and connected apps."""
        if capabilities is None:
            tools = list(self._tools.values())
        else:
            caps_lower = {c.lower() for c in capabilities}
            caps_lower.update({"system", "memory"})
            tools = [t for t in self._tools.values() if t.capability.lower() in caps_lower]

        # Fine-grained app-level filter if connected_apps is provided
        if connected_apps is not None:
            apps_upper = {canonical_app_slug(a) for a in connected_apps}
            filtered: List[BaseTool] = []
            for t in tools:
                if t.is_available_for(apps_upper):
                    filtered.append(t)
            tools = filtered

        return tools

    def get_deepgram_function_schemas(
        self,
        capabilities: Optional[List[str]] = None,
        connected_apps: Optional[List[str]] = None,
        include_meta_tools: bool = False,
    ) -> List[Dict[str, Any]]:
        """Export tool schemas formatted for Deepgram / Groq function calling.

        Excludes broad meta-tools like 'execute_app_action' by default to avoid semantic competition.
        """
        tools = self.get_tools_for_capabilities(capabilities, connected_apps=connected_apps)
        if not include_meta_tools:
            # Exclude broad catch-all dynamic execution meta-tools from live Deepgram schemas
            tools = [t for t in tools if t.name != "execute_app_action"]
        return [t.to_deepgram_schema() for t in tools]

    def get_metadata_catalog(self) -> List[Dict[str, Any]]:
        """Export complete tool contract metadata for permission, audit, and routing."""
        return [tool.get_metadata() for tool in self._tools.values()]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: str = "default_user",
        session_id: str = "",
        confirmed: bool = False,
        action_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a tool with safety confirmation policies, argument redaction, and user scoping."""
        tool = self.get_tool(tool_name)

        # Clean arguments: remove model confirmation tokens (model assertions are NEVER trusted)
        clean_args = {
            k: v for k, v in arguments.items()
            if k not in ("confirmed", "confirm", "user_confirmed")
        }

        # Safe logging: redact sensitive bodies, secrets, and auth tokens from operational logs (F15)
        safe_log_args = {
            k: ("***REDACTED***" if k.lower() in ("body", "password", "token", "key", "secret", "content") else str(v)[:60])
            for k, v in clean_args.items()
        }

        if not tool:
            logger.warning(f"Attempted to execute unregistered tool '{tool_name}'")
            return {
                "success": False,
                "error": f"Tool '{tool_name}' is not recognized.",
                "spoken_summary": f"I don't have access to the {tool_name} tool.",
            }

        # 1. Server-side Confirmation Policy Check for Write / Destructive Actions (F02)
        if tool.requires_confirmation:
            if action_id:
                # Validate and consume the exact pending action record
                consumed_ok, err_msg, _ = await pending_action_store.consume(
                    action_id=action_id,
                    user_id=user_id,
                    session_id=session_id,
                    expected_arguments=clean_args if clean_args else None,
                )

                if not consumed_ok:
                    logger.warning(f"Action '{action_id}' authorization failure: {err_msg}")
                    return {
                        "success": False,
                        "status": "authorization_error",
                        "error": err_msg or "Invalid or expired confirmation record.",
                        "spoken_summary": "I cannot proceed because the authorization is invalid or expired.",
                    }
                effective_confirmed = True
            elif confirmed is True:
                # Explicit code/test caller confirmation without action_id
                effective_confirmed = True
            else:
                effective_confirmed = False

            if not effective_confirmed:
                logger.info(f"Tool '{tool_name}' requires confirmation. Registering pending action for user '{user_id}'.")
                summary_proposal = self._generate_confirmation_proposal(tool_name, clean_args)
                pending_action = await pending_action_store.create(
                    tool_name=tool_name,
                    arguments=clean_args,
                    user_id=user_id,
                    session_id=session_id,
                    proposal_summary=summary_proposal,
                )
                return {
                    "success": False,
                    "status": "needs_confirmation",
                    "requires_confirmation": True,
                    "action_id": pending_action.action_id,
                    "tool_name": tool_name,
                    "arguments": clean_args,
                    "spoken_summary": summary_proposal,
                    "message": "Action paused pending user verbal confirmation.",
                }
        else:
            effective_confirmed = True

        # 2. Execution with Error Boundary and Deduplication
        from app.tools.execution_ledger import execution_ledger

        if tool.requires_confirmation:
            recent = execution_ledger.find_recent_execution(tool_name, clean_args, user_id, window_seconds=10.0)
            if recent:
                logger.info(f"Duplicate write execution prevented by ledger: {recent.receipt_id}")
                return {
                    "success": True,
                    "status": "already_executed",
                    "receipt_id": recent.receipt_id,
                    "message": "Action was already executed.",
                    "spoken_summary": recent.result_summary or "This action has already been performed.",
                }

        context = {"user_id": user_id, "session_id": session_id, "confirmed": effective_confirmed}
        try:
            logger.info(f"Executing tool '{tool_name}' (confirmed={effective_confirmed}, user={user_id}) with params: {safe_log_args}")
            merged_args = {**clean_args, **context}
            result = await tool.execute(**merged_args)

            # Never report success until the tool result confirms success
            if not result.get("success", False) and "error" in result:
                logger.warning(f"Tool '{tool_name}' returned unconfirmed failure: {result.get('error')}")

            # Record receipt in execution ledger
            if tool.requires_confirmation or getattr(tool, "category", "") == "action":
                status_str = "success" if result.get("success", False) else "failed"
                await execution_ledger.record_execution(
                    tool_name=tool_name,
                    arguments=clean_args,
                    user_id=user_id,
                    session_id=session_id,
                    status=status_str,
                    action_id=action_id,
                    result_summary=result.get("spoken_summary") or result.get("message") or "",
                )

            return result

        except Exception as e:
            logger.exception(f"Error executing tool '{tool_name}'")
            return {
                "success": False,
                "error": str(e),
                "spoken_summary": f"I encountered an issue executing {tool_name}.",
            }


    def _generate_confirmation_proposal(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Generate clear verbal confirmation proposal before executing write actions."""
        if tool_name == "send_email":
            recipient = args.get("recipient", "the recipient")
            subject = args.get("subject", "no subject")
            return f"I have prepared an email to {recipient} with the subject '{subject}'. Should I send it now?"
        elif tool_name == "create_calendar_event":
            title = args.get("title", "Event")
            start = args.get("start_time", "the requested time")
            return f"I am ready to schedule '{title}' for {start}. Would you like me to confirm this meeting?"
        return f"I am ready to perform {tool_name}. Would you like me to proceed?"

    def _register_default_tools(self) -> None:
        """Register core and workspace integration tools."""
        self.register(CurrentTimeTool())
        self.register(EndVoiceSessionTool())
        self.register(GetConnectedAppsTool())
        self.register(RunComplexTaskTool())
        self.register(ConfirmActionTool())
        self.register(ExecuteAppActionTool())
        self.register(SendEmailTool())
        self.register(SearchEmailsTool())
        self.register(CreateCalendarEventTool())
        self.register(ListCalendarEventsTool())
        self.register(SerpApiSearchTool())
        self.register(PerplexityResearchTool())
        self.register(TavilySearchTool())
        self.register(GoogleSheetsTool())
        self.register(GoogleDocsTool())
        self.register(GoogleDriveTool())
        self.register(SaveMemoryTool())
        self.register(SearchMemoryTool())


tool_registry = ToolRegistry()
