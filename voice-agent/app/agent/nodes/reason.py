"""Reason node: processes prompt and context using Groq LLM."""

from typing import Any, Dict, Optional
from langchain_core.runnables import RunnableConfig
from app.agent.persona.service import persona_service
from app.agent.state import AgentState
from app.integrations.llm.client import groq_client
from app.tools.registry import tool_registry


async def reason_node(state: AgentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Execute Groq LPU reasoning turn with tool calling and token streaming."""
    instructions = persona_service.get_voice_instructions(
        user_context=state.get("user_context", ""),
        memory_context=state.get("memory_context", ""),
    )

    messages = [{"role": "system", "content": instructions}]
    for msg in state.get("messages", []):
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

    tool_result = state.get("tool_result")
    if tool_result is not None:
        messages.append({"role": "system", "content": f"Tool execution result: {tool_result}"})

    # If we do not yet have a tool result, evaluate whether Groq calls a tool
    if tool_result is None:
        tools = tool_registry.get_openai_tool_schemas()
        if tools:
            try:
                reasoning_turn = await groq_client.chat_completion_with_tools(
                    messages=messages,
                    tools=tools,
                )
                tool_calls = reasoning_turn.get("tool_calls")
                if tool_calls:
                    # Activate the first requested tool call
                    return {
                        "active_tool_call": {
                            "name": tool_calls[0]["name"],
                            "arguments": tool_calls[0].get("arguments", {}),
                        }
                    }
            except Exception:
                # If tool evaluation fails, fall back to streaming conversation directly
                pass

    # Stream the conversational response
    on_token = None
    if config and isinstance(config, dict):
        on_token = config.get("configurable", {}).get("on_token")

    response_tokens = []
    async for token in groq_client.stream_chat_completion(messages=messages):
        response_tokens.append(token)
        if on_token:
            try:
                import inspect
                if inspect.iscoroutinefunction(on_token):
                    await on_token(token)
                else:
                    on_token(token)
            except Exception:
                pass

    full_response = "".join(response_tokens).strip()

    return {
        "response_text": full_response,
        "active_tool_call": None,
    }
