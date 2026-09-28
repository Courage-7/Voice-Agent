"""Server-side handling of Deepgram client-side function calls."""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable, Dict

from app.tools.distiller import speech_payload_distiller
from app.tools.registry import tool_registry

logger = logging.getLogger(__name__)

SendResponse = Callable[[Dict[str, Any]], Awaitable[None]]
IsCancelled = Callable[[str], bool]
OnEndSession = Callable[[], Awaitable[None]]


def _requested_functions(event: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Normalize both documented and compact Deepgram function-call events."""
    functions = event.get("functions", [])
    if isinstance(functions, list) and functions:
        return [function for function in functions if isinstance(function, dict)]
    return [{
        "id": event.get("function_call_id") or event.get("id") or "",
        "name": event.get("function_name") or event.get("name") or "",
        "arguments": event.get("input") or event.get("arguments") or {},
    }]


def _arguments(raw_arguments: Any) -> Dict[str, Any]:
    """Parse model arguments without accepting model-supplied authorization."""
    if isinstance(raw_arguments, str):
        try:
            parsed = json.loads(raw_arguments)
        except json.JSONDecodeError:
            parsed = {"query": raw_arguments}
    elif isinstance(raw_arguments, dict):
        parsed = dict(raw_arguments)
    else:
        parsed = {}

    for key in ("confirmed", "confirm", "user_confirmed"):
        parsed.pop(key, None)
    return parsed


async def execute_function_calls(
    event: Dict[str, Any],
    *,
    user_id: str,
    session_id: str,
    is_cancelled: IsCancelled,
    send_response: SendResponse,
    on_end_session: OnEndSession,
) -> None:
    """Execute client-side calls and return one response per uncancelled call."""
    for function in _requested_functions(event):
        call_id = str(function.get("id") or "")
        tool_name = str(function.get("name") or "")
        if not tool_name:
            logger.warning("[%s] Deepgram function request had no tool name.", session_id)
            continue
        if call_id and is_cancelled(call_id):
            logger.info("[%s] Skipping cancelled tool call %s", session_id, call_id)
            continue

        logger.info("[%s] Executing tool '%s' (call_id=%s).", session_id, tool_name, call_id)
        result = await tool_registry.execute_tool(
            tool_name=tool_name,
            arguments=_arguments(function.get("arguments", {})),
            user_id=user_id,
            session_id=session_id,
            confirmed=False,
        )

        if call_id and is_cancelled(call_id):
            logger.info("[%s] Suppressing response for cancelled tool call %s", session_id, call_id)
            continue

        content = speech_payload_distiller.distill(tool_name, result)
        await send_response({
            "type": "FunctionCallResponse",
            "id": call_id,
            "name": tool_name,
            "content": content,
        })

        if result.get("end_session"):
            await on_end_session()
