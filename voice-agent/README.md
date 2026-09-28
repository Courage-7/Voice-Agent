# Shinra (Backend Engine)

> **Main Platform Documentation**: Please refer to the root [README.md](../README.md) for the complete technical documentation, architecture diagrams, API specs, and interactive 3D frontend details.

[![Voice AI Agent System Architecture](../docs/architecture/voice_agent_architecture.png)](../docs/architecture/voice_agent_architecture.html)

---

## Quick Architecture Summary

The backend is built with **FastAPI**, **Deepgram Voice Agent WebSocket API**, **Groq LPU LLM Inference**, **LangGraph**, **Composio**, and **Neon Serverless PostgreSQL**:

* **Real-time Audio**: Streaming 16kHz linear16 PCM input, 24kHz linear16 synthesized audio output.
* **LLM Engine**: Groq Cloud LPU `llama-3.3-70b-versatile` with sub-300ms TTFT.
* **Tool Registry**: 17 built-in tools with strict write-action verbal confirmation policies.
* **Token Budget Gateway**: [`app/tools/distiller.py`](app/tools/distiller.py) enforcing a strict 1,200 character ceiling on tool results.
* **Long-Term Memory**: Neon Serverless PostgreSQL persistence via native asyncpg (`schema.sql`).

## Running Backend Tests

```bash
# From workspace root
uv sync --locked --extra dev
uv run --locked --extra dev python -m pytest -q
```

## Running Backend Locally

```bash
uv run --locked --extra dev python main.py
```

Run these commands from the repository root so the root lockfile and pytest configuration are used. The former test runners now delegate to pytest, including its isolated fixtures. See the root README for production packaging, demo mode, and artifact verification.
