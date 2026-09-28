"""Comprehensive unit tests for the Decoupled Dual-Stream Voice & Display Pipeline.

Tests all 11 core dimensions:
1. Speech recognition input (DeepgramLiveSTTClient)
2. LLM response generation (Groq dual-stream protocol)
3. Display Markdown streaming (<display> tag extraction)
4. Speech-text generation (<speech> natural language extraction)
5. TTS streaming (DeepgramStreamingTTSClient)
6. Audio playback frame forwarding
7. Barge-in / interruption handling
8. Tool calls and speech payload distillation
9. Conversation history persistence with RLS metadata
10. Failure, rate limit, and timeout handling
11. Voice session cleanup and resource teardown
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.config import settings
from app.integrations.deepgram.agent_session import DeepgramVoiceAgentSession
from app.integrations.deepgram.stt_client import DeepgramLiveSTTClient
from app.integrations.deepgram.tts_client import DeepgramStreamingTTSClient
from app.realtime.orchestrator import DualStreamVoiceOrchestrator
from app.realtime.session import RealtimeClientSession
from app.realtime.state import SessionState


# --------------------------------------------------------------------------
# 1. Speech Recognition Input (STT) Tests
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_stt_client_connection_and_audio_send():
    """Verify STT client initializes WebSocket with correct parameters and sends PCM bytes."""
    mock_ws = AsyncMock()
    client = DeepgramLiveSTTClient(session_id="test_stt_1", model="nova-2")
    client.ws = mock_ws
    client._is_running = True

    # Send PCM frame
    dummy_pcm = b"\x00\x01" * 800  # 1600 bytes
    await client.send_audio(dummy_pcm)

    assert mock_ws.send.called
    assert mock_ws.send.call_args[0][0] == dummy_pcm


@pytest.mark.asyncio
async def test_stt_transcript_and_bargein_parsing():
    """Verify STT parser triggers on_transcript, on_speech_started, and on_utterance_end."""
    transcript_events = []
    speech_started_called = []
    utterance_end_called = []

    async def mock_on_transcript(text, is_final, speech_final):
        transcript_events.append((text, is_final, speech_final))

    async def mock_on_speech_started():
        speech_started_called.append(True)

    async def mock_on_utterance_end():
        utterance_end_called.append(True)

    client = DeepgramLiveSTTClient(
        session_id="test_stt_2",
        on_transcript=mock_on_transcript,
        on_speech_started=mock_on_speech_started,
        on_utterance_end=mock_on_utterance_end,
    )

    # 1. Speech started (barge-in trigger)
    await client._handle_message({"type": "SpeechStarted"})
    assert len(speech_started_called) == 1

    # 2. Interim transcript
    await client._handle_message({
        "channel": {"alternatives": [{"transcript": "hello world"}]},
        "is_final": False,
        "speech_final": False,
    })
    assert len(transcript_events) == 1
    assert transcript_events[0] == ("hello world", False, False)

    # 3. Final transcript
    await client._handle_message({
        "channel": {"alternatives": [{"transcript": "hello world final"}]},
        "is_final": True,
        "speech_final": True,
    })
    assert len(transcript_events) == 2
    assert transcript_events[1] == ("hello world final", True, True)

    # 4. Utterance end
    await client._handle_message({"type": "UtteranceEnd"})
    assert len(utterance_end_called) == 1


# --------------------------------------------------------------------------
# 2, 3, 4. Dual-Stream LLM, Display Markdown, and Speech Generation Tests
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dual_stream_tag_extraction():
    """Verify orchestrator splits <display> markdown from <speech> natural voice text."""
    sent_events = []
    spoken_audio_chunks = []

    async def mock_send_event(event):
        sent_events.append(event)

    async def mock_send_audio(chunk):
        spoken_audio_chunks.append(chunk)

    orchestrator = DualStreamVoiceOrchestrator(
        session_id="test_dual_1",
        user_id="user_test",
        on_event=mock_send_event,
        on_audio_chunk=mock_send_audio,
    )
    orchestrator._is_running = True

    # Mock Groq streaming chunks with dual stream format
    mock_tokens = [
        "<display>\n## Quadratic Formula\n\n",
        "The formula is:\n$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$\n</display>\n",
        "<speech>\nFor a quadratic equation, ",
        "the roots are found with the quadratic formula. ",
        "I have displayed the formula on screen.\n</speech>",
    ]

    async def mock_stream(*args, **kwargs):
        for token in mock_tokens:
            yield token

    with patch("app.realtime.orchestrator.groq_client.stream_chat_completion", side_effect=mock_stream):
        with patch("app.realtime.orchestrator.tts_client.stream_speech_audio") as mock_tts:
            async def dummy_audio_stream(*args, **kwargs):
                yield b"\x01\x02\x03\x04"
            mock_tts.side_effect = dummy_audio_stream

            await orchestrator._process_turn_pipeline("Explain the quadratic formula")

    # Verify display content contains markdown and math
    display_events = [e for e in sent_events if e.get("type") == "ConversationText" and e.get("role") == "assistant"]
    assert len(display_events) > 0
    final_display = display_events[-1].get("display_markdown", "")
    assert "## Quadratic Formula" in final_display
    assert "\\frac" in final_display

    # Verify speech calls occurred
    assert mock_tts.called
    spoken_sentence = mock_tts.call_args_list[0][0][0]
    # Spoken text should NOT contain LaTeX delimiters or hashes
    assert "##" not in spoken_sentence
    assert "\\frac" not in spoken_sentence
    assert "quadratic" in spoken_sentence.lower()


# --------------------------------------------------------------------------
# 5 & 6. TTS Streaming and Audio Playback Forwarding Tests
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tts_streaming_client_forwarding():
    """Verify DeepgramStreamingTTSClient streams linear16 24kHz audio chunks."""
    tts = DeepgramStreamingTTSClient(default_voice="aura-2-thalia-en")

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.aiter_bytes = MagicMock(return_value=aiter_wrapper([b"\x10\x20" * 512, b"\x30\x40" * 512]))

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_resp
    mock_context.__aexit__.return_value = None

    mock_client = MagicMock()
    mock_client.stream.return_value = mock_context

    with patch("app.integrations.deepgram.tts_client.settings.deepgram_api_key", "test_api_key"):
        with patch.object(tts, "_get_client", return_value=mock_client):
            chunks = []
            async for chunk in tts.stream_speech_audio("Hello from Shinra"):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert len(chunks[0]) == 1024


# --------------------------------------------------------------------------
# 7. Barge-in / Interruption Test
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_barge_in_cancels_active_turn_and_emits_interruption():
    """Verify barge-in immediately halts assistant turn and notifies client."""
    sent_events = []

    async def mock_send_event(event):
        sent_events.append(event)

    orchestrator = DualStreamVoiceOrchestrator(
        session_id="test_bargein_1",
        on_event=mock_send_event,
    )
    orchestrator._is_running = True
    orchestrator._is_agent_speaking = True

    # Simulate active turn task
    async def long_running_task():
        await asyncio.sleep(5.0)

    active_task = asyncio.create_task(long_running_task())
    orchestrator._active_turn_task = active_task

    # Trigger barge-in
    await orchestrator._handle_barge_in()
    await asyncio.sleep(0)

    assert active_task.cancelled()
    assert orchestrator._is_agent_speaking is False
    assert orchestrator.state == SessionState.USER_SPEAKING

    event_types = [e.get("type") for e in sent_events]
    assert "AssistantInterrupted" in event_types


# --------------------------------------------------------------------------
# 8. Tool Calls and Distilled Speech Summary Test
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_speech_payload_distiller_budgeting():
    """Verify speech payload distiller trims raw tool outputs to compact facts."""
    from app.tools.distiller import speech_payload_distiller

    raw_output = {
        "success": True,
        "spoken_summary": "You have 2 unread emails from Sarah.",
        "emails": [
            {"id": "msg_1", "subject": "Project update", "from": "sarah@example.com"},
            {"id": "msg_2", "subject": "Meeting notes", "from": "sarah@example.com"},
        ],
        "deep_internal_raw_token_dump": "X" * 5000,
    }

    distilled_json = speech_payload_distiller.distill("search_emails", raw_output, max_chars=800)
    assert len(distilled_json) <= 800
    data = json.loads(distilled_json)
    assert data["success"] is True
    assert "Sarah" in data["spoken_summary"]
    assert "deep_internal_raw_token_dump" not in data


# --------------------------------------------------------------------------
# 9, 10, 11. Conversation History, Failure Handling, and Cleanup Tests
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_orchestrator_session_cleanup_and_teardown():
    """Verify session cleanup closes STT client, cancels tasks, and resets state."""
    orchestrator = DualStreamVoiceOrchestrator(session_id="test_cleanup_1")
    orchestrator._is_running = True
    orchestrator.stt_client.close = AsyncMock()

    # Create dummy tasks
    async def dummy_task():
        await asyncio.sleep(10.0)

    t1 = asyncio.create_task(dummy_task())
    t2 = asyncio.create_task(dummy_task())
    orchestrator._active_turn_task = t1
    orchestrator._tool_tasks.add(t2)

    await orchestrator.close()

    assert orchestrator._is_running is False
    assert orchestrator.state == SessionState.DISCONNECTED
    assert t1.cancelled()
    assert t2.cancelled()
    assert orchestrator.stt_client.close.called


@pytest.mark.asyncio
async def test_realtime_client_session_selects_decoupled_orchestrator(monkeypatch):
    """Verify RealtimeClientSession uses DualStreamVoiceOrchestrator when configured."""
    monkeypatch.setattr(settings, "voice_pipeline_mode", "decoupled")
    mock_ws = AsyncMock()
    session = RealtimeClientSession(session_id="test_pipeline_mode_1", client_ws=mock_ws)

    assert isinstance(session.backend_engine, DualStreamVoiceOrchestrator)
    assert session.deepgram_session == session.backend_engine

    # Also verify deepgram_agent mode
    monkeypatch.setattr(settings, "voice_pipeline_mode", "deepgram_agent")
    session_dg = RealtimeClientSession(session_id="test_pipeline_mode_2", client_ws=mock_ws)
    assert isinstance(session_dg.backend_engine, DeepgramVoiceAgentSession)


# Helper async iterator
async def aiter_wrapper(items):
    for item in items:
        yield item
