from enum import StrEnum

class ClientEventType(StrEnum):
    SESSION_START = "client.session.start"
    AUDIO = "client.audio"
    INTERRUPT = "client.interrupt"
    CANCEL = "client.cancel"
    SESSION_END = "client.session.end"

class ServerEventType(StrEnum):
    SESSION_READY = "server.session.ready"
    TRANSCRIPT_INTERIM = "server.transcript.interim"
    TRANSCRIPT_FINAL = "server.transcript.final"
    AGENT_THINKING = "server.agent.thinking"
    TOOL_STARTED = "server.tool.started"
    TOOL_COMPLETED = "server.tool.completed"
    TTS_AUDIO = "server.tts.audio"
    RESPONSE_COMPLETED = "server.response.completed"
    INTERRUPTED = "server.interrupted"
    ERROR = "server.error"
