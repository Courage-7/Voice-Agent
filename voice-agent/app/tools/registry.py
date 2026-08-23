"""Central tool registry and policy engine for Voice AI Agent."""

import logging
from typing import Any, Dict, List, Optional

from app.tools.base import BaseTool
from app.tools.calendar.tools import CreateCalendarEventTool, ListCalendarEventsTool
from app.tools.email.tools import SearchEmailsTool, SendEmailTool
from app.tools.memory.save_memory import SaveMemoryTool
from app.tools.memory.search_memory import SearchMemoryTool
from app.tools.search.tools import PerplexityResearchTool, SerpApiSearchTool
from app.tools.system.connected_apps import GetConnectedAppsTool
from app.tools.system.current_time import CurrentTimeTool
from app.tools.system.end_session import EndVoiceSessionTool
from app.tools.workspace.dynamic_action import ExecuteAppActionTool
from app.tools.workspace.tools import GoogleDocsTool, GoogleDriveTool, GoogleSheetsTool

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
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def get_all_tools(self) -> List[BaseTool]:
        """Get list of all registered tools."""
        return list(self._tools.values())

    def get_tools_by_capability(self, capability: str) -> List[BaseTool]:
        """Retrieve subset of tools matching a specific capability (e.g. 'email', 'calendar')."""
        return [t for t in self._tools.values() if t.capability.lower() == capability.lower()]

    def get_tools_for_capabilities(self, capabilities: List[str]) -> List[BaseTool]:
        """Retrieve small relevant tool subset matching allowed capabilities."""
        caps_lower = {c.lower() for c in capabilities}
        return [t for t in self._tools.values() if t.capability.lower() in caps_lower or t.capability == "system"]

    def get_deepgram_function_schemas(self, capabilities: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Export tool schemas formatted for Deepgram / Groq function calling, optionally scoped by capabilities."""
        tools = self.get_tools_for_capabilities(capabilities) if capabilities else self.get_all_tools()
        return [tool.to_deepgram_function_schema() for tool in tools]

    def get_metadata_catalog(self) -> List[Dict[str, Any]]:
        """Export complete tool contract metadata for permission, audit, and routing."""
        return [tool.get_metadata() for tool in self._tools.values()]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        confirmed: bool = False,
        **context: Any,
    ) -> Dict[str, Any]:
        """Execute a tool by name with policy checks (confirmation, timeout, validation)."""
        tool = self.get_tool(tool_name)
        if not tool:
            logger.error(f"Attempted to execute unregistered tool: {tool_name}")
            return {
                "success": False,
                "error": f"Tool '{tool_name}' is not recognized.",
                "spoken_summary": f"I don't have access to the {tool_name} tool.",
            }

        # 1. Confirmation Policy Check for Write / Destructive Actions
        if tool.requires_confirmation and not confirmed:
            logger.info(f"Tool '{tool_name}' requires confirmation. Halting for user approval.")
            summary_proposal = self._generate_confirmation_proposal(tool_name, arguments)
            return {
                "success": False,
                "requires_confirmation": True,
                "tool_name": tool_name,
                "arguments": arguments,
                "spoken_summary": summary_proposal,
                "message": "Action paused pending user verbal confirmation.",
            }

        # 2. Execution with Error Boundary
        try:
            logger.info(f"Executing tool '{tool_name}' (confirmed={confirmed}) with args: {arguments}")
            merged_args = {**arguments, **context}
            result = await tool.execute(**merged_args)

            # Never report success until the tool result confirms success
            if not result.get("success", False) and "error" in result:
                logger.warning(f"Tool '{tool_name}' returned unconfirmed failure: {result.get('error')}")

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
        self.register(ExecuteAppActionTool())
        self.register(SendEmailTool())
        self.register(SearchEmailsTool())
        self.register(CreateCalendarEventTool())
        self.register(ListCalendarEventsTool())
        self.register(SerpApiSearchTool())
        self.register(PerplexityResearchTool())
        self.register(GoogleSheetsTool())
        self.register(GoogleDocsTool())
        self.register(GoogleDriveTool())
        self.register(SaveMemoryTool())
        self.register(SearchMemoryTool())


tool_registry = ToolRegistry()
