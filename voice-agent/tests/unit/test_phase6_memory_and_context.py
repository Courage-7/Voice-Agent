"""Unit tests for Phase 6: Memory & Context Integration and Interruption Reconciliation."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.conversations.service import conversation_service
from app.integrations.deepgram.agent_session import DeepgramVoiceAgentSession
from app.memory.service import memory_service
from app.users.models import UserProfile
from app.users.service import user_service


@pytest.mark.asyncio
async def test_memory_summary_retrieval_and_prompt_injection():
    """Verify recent user memories are fetched and injected into Deepgram Settings prompt."""
    user_id = "user_mem_test_88"

    # Save test memories
    await memory_service.save_memory(user_id=user_id, content="Prefers morning meetings", category="calendar")
    await memory_service.save_memory(user_id=user_id, content="Lives in Seattle", category="location")

    session = DeepgramVoiceAgentSession(
        session_id="sess_mem_test",
        user_id=user_id,
    )
    mock_ws = AsyncMock()
    session.ws = mock_ws
    session._is_running = True

    await session._send_settings_configuration()
    assert mock_ws.send.called
    sent_payload = json.loads(mock_ws.send.call_args[0][0])

    prompt = sent_payload["agent"]["think"]["prompt"]
    assert "RELEVANT USER MEMORIES & PREFERENCES" in prompt
    assert "Prefers morning meetings" in prompt
    assert "Lives in Seattle" in prompt


@pytest.mark.asyncio
async def test_user_profile_context_injection():
    """Verify user profile name and context are injected into Deepgram Settings prompt."""
    user_id = "user_prof_test_99"
    await user_service.repository.save(UserProfile(id=user_id, full_name="Samantha Ray"))

    session = DeepgramVoiceAgentSession(
        session_id="sess_prof_test",
        user_id=user_id,
    )
    mock_ws = AsyncMock()
    session.ws = mock_ws
    session._is_running = True

    await session._send_settings_configuration()
    sent_payload = json.loads(mock_ws.send.call_args[0][0])
    prompt = sent_payload["agent"]["think"]["prompt"]

    assert "USER PROFILE & CONTEXT" in prompt
    assert "Samantha Ray" in prompt


@pytest.mark.asyncio
async def test_memory_service_graceful_fallback_on_error():
    """Verify session starts cleanly even if memory service raises an exception."""
    session = DeepgramVoiceAgentSession(
        session_id="sess_err_test",
        user_id="user_err",
    )
    mock_ws = AsyncMock()
    session.ws = mock_ws
    session._is_running = True

    with patch.object(memory_service, "get_user_memory_summary", side_effect=Exception("Database offline")):
        await session._send_settings_configuration()
        assert mock_ws.send.called


@pytest.mark.asyncio
async def test_interrupted_turn_transcript_reconciliation():
    """Verify assistant turns interrupted by user barge-in are tagged with interrupted=True metadata."""
    session_id = "sess_interruption_test"
    user_id = "user_interruption"
    session = DeepgramVoiceAgentSession(session_id=session_id, user_id=user_id)

    # 1. Agent starts speaking
    await session._handle_server_event({"type": "AgentStartedSpeaking"})
    assert session._is_agent_speaking is True
    assert session._last_assistant_turn_interrupted is False

    # 2. User interrupts (barge-in)
    await session._handle_server_event({"type": "UserStartedSpeaking"})
    assert session._is_agent_speaking is False
    assert session._last_assistant_turn_interrupted is True

    # 3. Transcript logging occurs for interrupted assistant turn
    await session._handle_server_event({
        "type": "ConversationText",
        "role": "assistant",
        "content": "I was about to tell you the weather forecast when you spoke...",
    })

    conv = conversation_service.get_session(session_id)
    assert conv is not None
    assert len(conv.messages) >= 1
    last_msg = conv.messages[-1]
    assert last_msg.role == "assistant"
    assert last_msg.metadata.get("interrupted") is True

    # 4. Normal uninterrupted turn
    await session._handle_server_event({"type": "AgentStartedSpeaking"})
    await session._handle_server_event({"type": "AgentAudioDone"})
    assert session._last_assistant_turn_interrupted is False

    await session._handle_server_event({
        "type": "ConversationText",
        "role": "assistant",
        "content": "This turn completed fully without interruption.",
    })
    last_msg_clean = conv.messages[-1]
    assert last_msg_clean.metadata.get("interrupted") is not True
