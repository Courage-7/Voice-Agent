"""Search and research tools: SerpAI and Perplexity AI via Composio OAuth."""

from typing import Any, Dict
from app.integrations.composio.client import composio_gateway
from app.tools.base import BaseTool


class SerpApiSearchTool(BaseTool):
    """Tool to perform real-time web searches using SerpAI connected via Composio."""

    name = "web_search_serpapi"
    description = "Search the web for up-to-date real-time information, news, and facts."
    capability = "search"
    read_only = True
    requires_confirmation = False
    timeout_seconds = 10.0

    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search terms or question."},
        },
        "required": ["query"],
    }

    async def execute(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", "default_user")
        res = await composio_gateway.execute_action("SERPAPI_SEARCH", {"query": query}, entity_id=user_id)
        if res.get("success"):
            return {
                "success": True,
                "spoken_summary": f"Here is what I found online for '{query}'.",
                "results": res.get("data", {}),
            }
        return {
            "success": False,
            "spoken_summary": res.get("spoken_summary", f"Search for '{query}' could not be completed."),
            "error": res.get("error", "Search failed"),
        }


class PerplexityResearchTool(BaseTool):
    """Tool for deep online AI synthesis and research via Perplexity connected via Composio."""

    name = "perplexity_ai_research"
    description = "Perform deep AI-powered web research and fact-finding for complex questions."
    capability = "search"
    read_only = True
    requires_confirmation = False
    timeout_seconds = 15.0

    parameters = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "The detailed research query or topic."},
        },
        "required": ["prompt"],
    }

    async def execute(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", "default_user")
        res = await composio_gateway.execute_action("PERPLEXITYAI_PERPLEXITY_AI_SEARCH", {"query": prompt}, entity_id=user_id)
        if res.get("success"):
            return {
                "success": True,
                "spoken_summary": f"Here is the research summary for '{prompt}'.",
                "results": res.get("data", {}),
            }
        return {
            "success": False,
            "spoken_summary": res.get("spoken_summary", f"Research for '{prompt}' could not be completed."),
            "error": res.get("error", "Research failed"),
        }
