"""Load context node: retrieves user profile and long-term memory."""

from typing import Any, Dict
from app.agent.state import AgentState
from app.memory.service import memory_service
from app.users.service import user_service


async def load_context_node(state: AgentState) -> Dict[str, Any]:
    """Fetch user profile and relevant memories from Supabase."""
    user_id = state.get("user_id", "default_user")
    user = await user_service.get_or_create_user(user_id)
    memories_summary = await memory_service.get_user_memory_summary(user_id)

    user_context = f"User Name: {user.full_name}, Timezone: {user.timezone}, Preferred Persona: {user.preferred_persona}"

    return {
        "user_context": user_context,
        "memory_context": memories_summary,
    }
