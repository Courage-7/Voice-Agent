"""Real-time voice session state enumeration."""

from enum import Enum


class SessionState(str, Enum):
    """Lifecycle state of a voice session."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    LISTENING = "listening"
    USER_SPEAKING = "user_speaking"
    THINKING = "thinking"
    TOOL_EXECUTION = "tool_execution"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    DISCONNECTED = "disconnected"
    ERROR = "error"
