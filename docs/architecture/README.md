# Voice AI Agent System Architecture

This directory contains the single, comprehensive, interactive architecture diagram for the entire **Voice AI Agent** platform.

---

## 🧭 Interactive Architecture Viewer
Open the standalone interactive diagram in your browser:
* **[Interactive Architecture Viewer (HTML)](./voice_agent_architecture.html)**
* **[Architecture Specification (JSON)](./voice_agent_architecture.json)**

---

## 🧩 Architectural Subsystems Covered

```
+-------------------------------------------------------------------------------------------------------------+
|                                     VOICE AI AGENT SYSTEM ARCHITECTURE                                     |
+-------------------------------------------------------------------------------------------------------------+
|                                                                                                             |
|  [ Tool Defense & Execution Hub ]                                                                           |
|  [ Speech Token Distiller ] ------ budgeted execution ------> [ Tool Registry & OAuth ]                   |
|  (1,200 Char Hard Ceiling)                                     (13 Tools / Composio Hub)                    |
|           ^                                                                                                 |
|           | (tool call dispatch)                                                                            |
|           |                                                                                                 |
|  [ Realtime Voice Streaming Highway ]                                                                       |
|  [ Three.js Cyber HUD ] --- 16kHz PCM ---> [ FastAPI Realtime Core ] --- live stream ---> [ Deepgram Agent ]|
|  (React 18 / Web Audio)                   (WebSocket /ws/agent)                           (Nova-2 / Aura-2) |
|           |                                       |                                              |          |
|           | (human voice rules)                   | (p50/p95/p99)                                | (tokens) |
|           v                                       v                                              v          |
|  [ Persona & Voice Engine ]               [ Telemetry & Metrics ]                        [ Groq LPU Engine ]|
|  (5 Human Persona Skills)                 (Prometheus Latency)                           (Sub-300ms TTFT)   |
|                                                   |                                              |          |
|                                                   | (memories & state)                           | (plans)  |
|                                                   v                                              v          |
|                                           [ Supabase PostgreSQL ] <------ checkpoints --- [ Complex Planner ]|
|                                           (Durable State / Vector)                       (Multi-Step Engine)|
|                                                                                                             |
+-------------------------------------------------------------------------------------------------------------+
```

1. **Sub-300ms Realtime Voice Loop:**
   - **Three.js Cyber HUD:** Full-duplex Web Audio API capturing 16kHz linear16 PCM with zero-gain mic feedback mute.
   - **FastAPI Realtime Core:** WebSocket `/ws/agent` streaming audio chunks to Deepgram Nova-2 STT with instant barge-in interruption.
   - **Deepgram Voice Agent API:** Streaming speech recognition, native VAD, and Aura-2 TTS synthesis.
   - **Groq LPU Engine:** Ultra-fast conversational inference (`openai/gpt-oss-120b`).
2. **Tool Defense & Context Protection:**
   - **Speech Token Distiller:** Enforces a strict 1,200 character ceiling (~300 tokens) on all tool returns to prevent LLM context exhaustion.
   - **Tool Registry & OAuth:** Manages 13 tools (Gmail, Google Calendar, Drive, Docs, Sheets, Perplexity, SerpApi) with confirmation barriers on write actions.
3. **State Persistence, Prompts & Observability:**
   - **Persona & Voice Engine:** Formats human spoken English, natural contractions, breathing pauses (`--`), and 5 persona skills.
   - **Supabase PostgreSQL:** Durable multi-turn transcripts, user profiles, and vector memories.
   - **Complex Task Engine:** Multi-step action decomposition, execution pausing, and resumption.
   - **Prometheus Telemetry:** Live collection of latency percentiles (p50, p95, p99) and turn counters.

---

## 🚀 How to Run the Interactive Architecture Page

You can launch the interactive architecture page in your default browser using any of the following commands:

### 1. Via NPM (Cross-Platform)
From the repository root or `frontend/`:
```bash
npm run architecture
```
*(or shorthand `npm run arch`)*

### 2. Via Windows Quick Launcher
In PowerShell or Command Prompt from the repository root:
```powershell
.\run_architecture.cmd
```

### 3. Native PowerShell / Shell
* **Windows (PowerShell):**
  ```powershell
  Start-Process "docs\architecture\voice_agent_architecture.html"
  ```
* **macOS:**
  ```bash
  open docs/architecture/voice_agent_architecture.html
  ```
* **Linux:**
  ```bash
  xdg-open docs/architecture/voice_agent_architecture.html
  ```

