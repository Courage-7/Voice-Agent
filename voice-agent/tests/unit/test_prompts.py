"""Unit tests for Voice Agent prompt and persona engine."""

from app.agent.persona.service import persona_service
from app.agent.prompts.personas import get_persona_prompt
from app.agent.prompts.system import build_system_prompt


def test_system_prompt_builder():
    """Verify system prompt enforces plain text and voice guidelines."""
    prompt = build_system_prompt(
        persona_instructions="Executive tone",
        user_context="User Name: Alice",
        memory_context="Prefers concise updates",
    )

    assert "CRITICAL VOICE DELIVERY RULES" in prompt
    assert "PLAIN SPOKEN TEXT ONLY" in prompt
    assert "Executive tone" in prompt
    assert "Alice" in prompt
    assert "concise updates" in prompt


def test_persona_retrieval():
    """Verify personas can be fetched properly."""
    assert "executive personal assistant" in get_persona_prompt("executive").lower()
    assert "friendly" in get_persona_prompt("casual").lower()
    assert "research assistant" in get_persona_prompt("researcher").lower()


def test_persona_service_prompt():
    """Verify persona service produces complete system prompt."""
    instructions = persona_service.get_voice_instructions(user_context="User ID: 123")
    assert "CRITICAL VOICE DELIVERY RULES" in instructions
    assert "User ID: 123" in instructions
