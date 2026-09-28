"""Search and research tools: SerpAI and Perplexity AI via Composio OAuth."""

from typing import Any, Dict
from app.integrations.composio.client import composio_gateway
from app.tools.base import BaseTool


def _extract_serp_results(data: Any) -> Any:
    """Extract top concise answer or snippet from raw SerpApi response."""
    if not isinstance(data, dict):
        return str(data)[:400]
    
    # 1. Direct answer box or knowledge graph snippet
    answer_box = data.get("answer_box") or {}
    if isinstance(answer_box, dict):
        answer = answer_box.get("answer") or answer_box.get("snippet") or answer_box.get("title")
        if answer:
            return str(answer)[:350]

    kg = data.get("knowledge_graph") or {}
    if isinstance(kg, dict):
        desc = kg.get("description")
        if desc:
            return str(desc)[:350]

    # 2. Organic results - top 3 concise summaries
    organic = data.get("organic_results") or data.get("results") or []
    if isinstance(organic, list):
        items = []
        for item in organic[:3]:
            if isinstance(item, dict):
                title = str(item.get("title") or "")[:70]
                snippet = str(item.get("snippet") or "")[:150]
                if title or snippet:
                    items.append(f"{title}: {snippet}")
            elif isinstance(item, str):
                items.append(item[:150])
        if items:
            return items

    return {k: str(v)[:100] for k, v in list(data.items())[:3]}


def _extract_perplexity_results(data: Any) -> str:
    """Extract clean answer text from Perplexity response."""
    if isinstance(data, str):
        return data[:500]
    if isinstance(data, dict):
        # Check common response keys
        ans = data.get("text") or data.get("answer") or data.get("response") or data.get("content")
        if ans:
            return str(ans)[:500]
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message", {})
            if isinstance(msg, dict) and msg.get("content"):
                return str(msg.get("content"))[:500]
        # Fallback to distillation of inner keys
        return str(list(data.values())[0])[:500] if data else "No content returned."
    return str(data)[:400]


class SerpApiSearchTool(BaseTool):
    """Tool to perform real-time web searches using SerpAI connected via Composio."""

    name = "web_search_serpapi"
    description = "Search the web for up-to-date real-time information, news, and facts."
    capability = "search"
    supported_connected_apps = ("SERPAPI",)
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
            extracted = _extract_serp_results(res.get("data", {}))
            return {
                "success": True,
                "spoken_summary": f"Here is what I found online for '{query}'.",
                "results": extracted,
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
    supported_connected_apps = ("PERPLEXITYAI",)
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
            extracted = _extract_perplexity_results(res.get("data", {}))
            return {
                "success": True,
                "spoken_summary": f"Here is the research summary for '{prompt}'.",
                "results": extracted,
            }
        return {
            "success": False,
            "spoken_summary": res.get("spoken_summary", f"Research for '{prompt}' could not be completed."),
            "error": res.get("error", "Research failed"),
        }


def _extract_tavily_results(data: Any) -> Any:
    """Extract clean answer text and top snippets from raw Tavily response."""
    if not isinstance(data, dict):
        return str(data)[:400]

    inner = data.get("response_data") or data.get("data") or data
    if not isinstance(inner, dict):
        return str(inner)[:400]

    # 1. Direct synthesized answer if available
    answer = inner.get("answer")
    if answer and isinstance(answer, str):
        clean_ans = answer.strip()
        if len(clean_ans) > 20:
            return clean_ans[:400]

    # 2. Organic results - top 3 concise summaries
    results = inner.get("results") or []
    if isinstance(results, list) and results:
        items = []
        for item in results[:3]:
            if isinstance(item, dict):
                title = str(item.get("title") or "")[:70]
                snippet = str(item.get("content") or item.get("snippet") or "")[:150]
                if title or snippet:
                    items.append(f"{title}: {snippet}")
            elif isinstance(item, str):
                items.append(item[:150])
        if items:
            return items

    return {k: str(v)[:100] for k, v in list(inner.items())[:3]}


class TavilySearchTool(BaseTool):
    """Tool to perform real-time factual web searches using Tavily connected via Composio."""

    name = "tavily_search"
    description = "Search the web using Tavily for high-accuracy, factual, AI-synthesized real-time search results."
    capability = "search"
    supported_connected_apps = ("TAVILY",)
    read_only = True
    requires_confirmation = False
    timeout_seconds = 12.0

    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query or factual question to look up online."},
            "search_depth": {
                "type": "string",
                "enum": ["basic", "advanced"],
                "default": "basic",
                "description": "Search depth: 'basic' for standard search or 'advanced' for deeper research.",
            },
            "max_results": {
                "type": "integer",
                "default": 3,
                "description": "Maximum number of search results to retrieve.",
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", "default_user")
        search_depth = kwargs.get("search_depth", "basic")
        max_results = kwargs.get("max_results", 3)
        params = {
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": True,
        }
        res = await composio_gateway.execute_action("TAVILY_SEARCH", params, entity_id=user_id)
        if res.get("success"):
            extracted = _extract_tavily_results(res.get("data", {}))
            spoken = f"Here is what I found on Tavily for '{query}'."
            if isinstance(extracted, str) and len(extracted) < 160:
                spoken = extracted
            return {
                "success": True,
                "spoken_summary": spoken,
                "results": extracted,
            }
        return {
            "success": False,
            "spoken_summary": res.get("spoken_summary", f"Search for '{query}' could not be completed on Tavily."),
            "error": res.get("error", "Tavily search failed"),
        }
