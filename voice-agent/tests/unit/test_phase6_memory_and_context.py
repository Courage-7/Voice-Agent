"""Unit tests for Phase 6: Memory & Context Integration and Interruption Reconciliation."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.conversations.service import conversation_service
from app.memory.service import memory_service
from app.realtime.orchestrator import DualStreamVoiceOrchestrator
from app.realtime.state import SessionState
from app.users.models import UserProfile
from app.users.service import user_service


@pytest.mark.asyncio
async def test_memory_summary_retrieval_and_prompt_injection():
    """Verify recent user memories are fetched and injected into orchestrator context."""
    user_id = "user_mem_test_88"

    # Save test memories
    await memory_service.save_memory(user_id=user_id, content="Prefers morning meetings", category="calendar")
    await memory_service.save_memory(user_id=user_id, content="Lives in Seattle", category="location")

    session = DualStreamVoiceOrchestrator(
        session_id="sess_mem_test",
        user_id=user_id,
    )
    await session._load_session_context()

    assert "Prefers morning meetings" in session._memory_summary
    assert "Lives in Seattle" in session._memory_summary


@pytest.mark.asyncio
async def test_user_profile_context_injection():
    """Verify user profile name and context are injected into orchestrator context."""
    user_id = "user_prof_test_99"
    await user_service.repository.save(UserProfile(id=user_id, full_name="Samantha Ray"))

    session = DualStreamVoiceOrchestrator(
        session_id="sess_prof_test",
        user_id=user_id,
    )
    await session._load_session_context()

    assert session._user_name == "Samantha"
    assert "Samantha Ray" in session._user_context_str


@pytest.mark.asyncio
async def test_memory_service_graceful_fallback_on_error():
    """Verify session starts cleanly even if memory service raises an exception."""
    session = DualStreamVoiceOrchestrator(
        session_id="sess_err_test",
        user_id="user_err",
    )
    with patch.object(memory_service, "get_user_memory_summary", side_effect=Exception("Database offline")):
        await session._load_session_context()
        assert session._memory_summary == ""


@pytest.mark.asyncio
async def test_interrupted_turn_barge_in():
    """Verify active assistant turns are interrupted by user barge-in."""
    events = []

    async def on_event(evt):
        events.append(evt)

    session = DualStreamVoiceOrchestrator(
        session_id="sess_interruption_test",
        user_id="user_interruption",
        on_event=on_event,
    )
    session._is_agent_speaking = True

    await session._handle_barge_in()

    assert session._is_agent_speaking is False
    assert session.state == SessionState.USER_SPEAKING
    assert any(evt.get("type") == "AssistantInterrupted" for evt in events)
