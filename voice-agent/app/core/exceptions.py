"""Custom domain and infrastructure exceptions."""


class VoiceAgentException(Exception):
    """Base exception for all Voice AI Agent errors."""
    pass


class STTConnectionError(VoiceAgentException):
    """Raised when Speech-to-Text service connection fails."""
    pass


class TTSSynthesisError(VoiceAgentException):
    """Raised when Text-to-Speech synthesis fails."""
    pass


class ToolExecutionError(VoiceAgentException):
    """Raised when external tool execution fails."""
    pass


class MemoryRepositoryError(VoiceAgentException):
    """Raised when Supabase or memory store access fails."""
    pass


class SessionNotFoundError(VoiceAgentException):
    """Raised when a requested voice session does not exist."""
    pass
