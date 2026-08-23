"""Shared constants across voice, agent, and audio modules."""

DEFAULT_INPUT_SAMPLE_RATE = 16000
DEFAULT_OUTPUT_SAMPLE_RATE = 24000
DEFAULT_AUDIO_CHANNELS = 1
DEFAULT_AUDIO_ENCODING = "linear16"

# Session timeouts (seconds)
DEFAULT_SESSION_TIMEOUT = 300
DEFAULT_TOOL_TIMEOUT = 10

# Roles
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM = "system"
ROLE_TOOL = "tool"
