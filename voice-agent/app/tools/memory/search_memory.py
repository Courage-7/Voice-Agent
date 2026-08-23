"""Tool to search user memories and context."""

from typing import Any, Dict

from app.memory.service import memory_service
from app.tools.base import BaseTool


class SearchMemoryTool(BaseTool):
    """Tool to search past memories, notes, and user preferences."""

    name = "search_user_memory"
    description = "Search long-term memory for user preferences, notes, past discussions, and facts."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search keyword or question to find relevant memories.",
            },
            "limit": {
                "type": "integer",
                "default": 3,
                "description": "Maximum number of memories to retrieve.",
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str, limit: int = 3, user_id: str = "default_user", **kwargs: Any) -> Dict[str, Any]:
        memories = await memory_service.search_memory(user_id=user_id, query=query, limit=limit)
        return {
            "success": True,
            "spoken_summary": f"Retrieved memories for '{query}'.",
            "memories": memories,
        }
