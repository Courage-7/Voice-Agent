# Voice AI Agent

Feature-oriented modular-monolith scaffold.

Core stack:
- FastAPI + WebSockets
- Deepgram STT/TTS
- LangGraph
- LangChain where useful
- LLM provider abstraction
- Composio
- Supabase

Architecture principle:

> Product capabilities own behavior. Infrastructure adapters own vendors.
> The agent orchestrates; it does not become the entire application.
