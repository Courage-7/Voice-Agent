"""Unit tests for Phase 5: Companion Prompt & Conversational Behavior."""

from app.agent.persona.config import PersonaConfig
from app.agent.persona.service import PersonaService
from app.agent.prompts.personas import get_persona_prompt
from app.agent.prompts.system import VOICE_AGENT_BASE_INSTRUCTIONS, build_system_prompt


def test_companion_default_persona_resolution():
    """Scenario 1: Verify companion is default persona and embodies warm attentive tone."""
    default_prompt = get_persona_prompt()
    assert "companion" in default_prompt.lower()
    assert "warm" in default_prompt.lower()
    assert "active listening" in default_prompt.lower()

    config = PersonaConfig()
    assert config.name == "companion"
    assert config.voice_model == "aura-2-thalia-en"


def test_plain_text_no_markdown_rule():
    """Scenario 2: Verify strict voice output constraints prohibiting markdown and emojis."""
    assert "PLAIN SPOKEN TEXT ONLY" in VOICE_AGENT_BASE_INSTRUCTIONS
    assert "NEVER use markdown formatting" in VOICE_AGENT_BASE_INSTRUCTIONS
    assert "no asterisks" in VOICE_AGENT_BASE_INSTRUCTIONS.lower()
    assert "no bullet points" in VOICE_AGENT_BASE_INSTRUCTIONS.lower()


def test_adaptive_sentence_length_rule():
    """Scenario 3: Verify adaptive response length (concise simple turns, 2-4 sentences for summaries)."""
    assert "ADAPTIVE LENGTH" in VOICE_AGENT_BASE_INSTRUCTIONS
    assert "1 to 2 short sentences" in VOICE_AGENT_BASE_INSTRUCTIONS
    assert "2 to 4 well-structured sentences" in VOICE_AGENT_BASE_INSTRUCTIONS


def test_reset_loop_elimination_rule():
    """Scenario 4: Verify elimination of repetitive 'How can I help you' reset loops on short affirmations."""
    assert "ELIMINATE REPETITIVE RESET LOOPS" in VOICE_AGENT_BASE_INSTRUCTIONS
    assert "DO NOT reset the conversation" in VOICE_AGENT_BASE_INSTRUCTIONS
    assert 'How can I help you today?' in VOICE_AGENT_BASE_INSTRUCTIONS


def test_tool_transitions_and_write_confirmation_rule():
    """Scenario 5: Verify natural tool transition phrasing and write confirmation requirements."""
    assert "NATURAL TOOL TRANSITIONS" in VOICE_AGENT_BASE_INSTRUCTIONS
    assert "ask for confirmation before executing" in VOICE_AGENT_BASE_INSTRUCTIONS


def test_friendly_error_translation_rule():
    """Scenario 6: Verify friendly spoken translation of tool errors without raw stack traces."""
    assert "Never report raw tool errors" in VOICE_AGENT_BASE_INSTRUCTIONS
    assert "Translate errors into friendly, reassuring spoken English" in VOICE_AGENT_BASE_INSTRUCTIONS


def test_system_prompt_builder_integration():
    """Verify complete system prompt construction integrates all runtime sections seamlessly."""
    prompt = build_system_prompt(
        persona_instructions="Attentive companion tone",
        user_context="User ID: user_alex",
        memory_context="Lives in San Francisco, prefers Outlook Calendar",
    )
    assert "CRITICAL VOICE DELIVERY RULES" in prompt
    assert "Attentive companion tone" in prompt
    assert "user_alex" in prompt
    assert "San Francisco" in prompt
