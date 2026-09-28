"""Regression tests for Deepgram client-side function dispatch."""

from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.deepgram.function_calls import execute_function_calls


@pytest.mark.asyncio
async def test_function_dispatch_strips_model_confirmation_and_returns_result():
    sent = []
    on_end_session = AsyncMock()

    async def send_response(payload):
        sent.append(payload)

    with patch(
        "app.integrations.deepgram.function_calls.tool_registry.execute_tool",
        new_callable=AsyncMock,
        return_value={"success": True, "spoken_summary": "Done."},
    ) as execute_tool:
        await execute_function_calls(
            {
                "functions": [{
                    "id": "call_1",
                    "name": "search_emails",
                    "arguments": '{"query":"new mail","confirmed":true}',
                }]
            },
            user_id="user_123",
            session_id="session_123",
            is_cancelled=lambda _: False,
            send_response=send_response,
            on_end_session=on_end_session,
        )

    assert execute_tool.await_args.kwargs["arguments"] == {"query": "new mail"}
    assert sent[0]["id"] == "call_1"
    assert sent[0]["name"] == "search_emails"
    on_end_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancelled_function_is_never_executed_or_answered():
    send_response = AsyncMock()

    with patch(
        "app.integrations.deepgram.function_calls.tool_registry.execute_tool",
        new_callable=AsyncMock,
    ) as execute_tool:
        await execute_function_calls(
            {"functions": [{"id": "call_2", "name": "send_email", "arguments": {}}]},
            user_id="user_123",
            session_id="session_123",
            is_cancelled=lambda call_id: call_id == "call_2",
            send_response=send_response,
            on_end_session=AsyncMock(),
        )

    execute_tool.assert_not_awaited()
    send_response.assert_not_awaited()
