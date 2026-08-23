"""Tool to persist user memory and preferences."""

from typing import Any, Dict

from app.memory.service import memory_service
from app.tools.base import BaseTool


class SaveMemoryTool(BaseTool):
    """Tool to save personal user facts, preferences, and recurring context."""

    name = "save_user_memory"
    description = "Save an important fact, preference, relationship, or instruction into long-term memory."
    parameters = {
        "type": "object",
        "properties": {
            "fact": {
                "type": "string",
                "description": "The atomic fact or preference to remember (e.g. 'User prefers morning meetings at 10 AM').",
            },
            "category": {
                "type": "string",
                "enum": ["preference", "personal", "work", "routine", "general"],
                "default": "general",
                "description": "Category for organizing the memory.",
            },
        },
        "required": ["fact"],
    }

    async def execute(self, fact: str, category: str = "general", user_id: str = "default_user", **kwargs: Any) -> Dict[str, Any]:
        res = await memory_service.save_memory(user_id=user_id, content=fact, category=category)
        return {
            "success": True,
            "spoken_summary": "I have remembered that for you.",
            "memory": res,
        }
