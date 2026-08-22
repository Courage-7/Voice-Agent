from enum import StrEnum

class SessionState(StrEnum):
    LISTENING = "listening"
    USER_SPEAKING = "user_speaking"
    ENDPOINT_DETECTED = "endpoint_detected"
    THINKING = "thinking"
    TOOL_EXECUTION = "tool_execution"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    CLOSED = "closed"
    ERROR = "error"
