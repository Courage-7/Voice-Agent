"""Reason node: processes prompt and context using Groq LLM."""

from typing import Any, Dict
from app.agent.persona.service import persona_service
from app.agent.state import AgentState
from app.integrations.llm.client import groq_client


async def reason_node(state: AgentState) -> Dict[str, Any]:
    """Execute Groq LPU reasoning turn."""
    instructions = persona_service.get_voice_instructions(
        user_context=state.get("user_context", ""),
        memory_context=state.get("memory_context", ""),
    )

    messages = [{"role": "system", "content": instructions}]
    for msg in state.get("messages", []):
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

    # Stream or generate response from Groq
    response_tokens = []
    async for token in groq_client.stream_chat_completion(messages=messages):
        response_tokens.append(token)

    full_response = "".join(response_tokens).strip()

    return {"response_text": full_response}
