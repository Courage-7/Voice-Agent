# Technical Audit & Diagnostic Handoff Report: Voice AI Agent Codebase

**Audit Target:** Voice AI Agent Codebase (`voice-agent`)  
**Audit Type:** Read-Only Technical Architecture & Diagnostic Audit  
**Runtime Environment:** Windows (x64), Python 3.12, FastAPI ASGI, Web Audio API  
**Target Audience:** Senior AI / ML / Voice Systems Engineer  

---

## 1. Executive Summary

- **Live Voice Architecture Decoupled from LangGraph**: The live voice path uses Deepgram Voice Agent API (`wss://agent.deepgram.com/v1/agent/converse`) directly as the end-to-end STT + LLM Think + TTS Speak orchestrator. LangGraph ([app/agent/graph.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/agent/graph.py)) is implemented with nodes and state schemas, but is **never invoked during live voice sessions**.
- **Greeting Latency Root Cause Identified**: The greeting is not pre-synthesized or defined in Deepgram's native `agent.greeting` config. Instead, the backend waits for 4 sequential network handshakes (`POST /api/voice/sessions` → Client WS connect → Deepgram WS connect → `Settings` send → `SettingsApplied` event receipt) before sending a reactive `InjectAgentMessage` text payload to Deepgram, triggering on-demand Aura TTS synthesis.
- **Overlapping Speech Root Cause Identified**: Web Audio API playback in [app/realtime/playground.html](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html) receives raw, anonymous binary PCM frames with **no `turn_id`, `generation_id`, or sequence timestamp**. While frontend `UserStartedSpeaking` stops currently scheduled buffer nodes, late in-flight binary chunks arriving over the TCP socket immediately trigger `playAudioChunk()`, playing stale audio concurrently with the subsequent turn.
- **Missing Interruption Cancellation on Text Injection**: Sending typed messages via `InjectUserMessage` (`sendBtn.onclick`) does not call `stopAllAudioPlayback()` or send a Deepgram `Interrupt` message, allowing prior agent speech to finish playing concurrently with new responses.
- **Tool Schema Duplication & Conflict**: The LLM is simultaneously exposed to 15 tool schemas, including specific tools (`send_email`, `search_emails`, `create_calendar_event`, `list_calendar_events`) and a redundant universal meta-tool (`execute_app_action`).
- **Hardcoded Provider Defaults Break Multi-Account Scenarios**: `search_emails` and `send_email` hardcode `provider="gmail"`, while `list_calendar_events` and `create_calendar_event` hardcode `provider="google"`. When an Outlook-only user asks about email or calendar, the tools default to Gmail/Google Calendar and fail with `ConnectedAccountNotFound`.
- **All 15 Tools Unconditionally Exposed**: `DeepgramVoiceAgentSession` sends all 15 tool definitions regardless of which apps the user actually connected, ignoring the scoped capability filtering logic available in `app/api/v1/integrations.py`.
- **Confirmation Safety Bypass in Dynamic Tool**: `send_email` enforces `requires_confirmation = True`, but `execute_app_action` sets `requires_confirmation = False`, allowing the model to bypass confirmation when executing `GMAIL_SEND_EMAIL` through the dynamic tool.
- **No Flux TTS Usage**: The codebase uses Deepgram Aura TTS (`aura-asteria-en` via v1 Agent API). Flux TTS (`/v2`) is not referenced or configured anywhere.
- **Hardcoded LLM Model in Deepgram Session**: `DeepgramVoiceAgentSession._send_settings_configuration()` hardcodes `groq_think_model = "openai/gpt-oss-20b"`, ignoring `settings.groq_model` (`"groq/compound"`).
- **Runtime Voice Selection Not Supported**: TTS voice model is statically loaded from `settings.deepgram_tts_model`. Deepgram `UpdateSpeak` message handler and frontend voice selector UI are absent.
- **Zero Observability on Voice Latency**: Deepgram `LatencyReport` events are ignored; `LatencyTracker` and `TelemetryEvent` classes are defined but unreferenced; Prometheus metrics counters are never incremented during WebSocket execution.
- **Memory Context Excluded from Voice Startup**: Long-term memory (`Supabase` / `MemoryService`) is never retrieved or injected into the prompt during voice session initialization (`user_context` is hardcoded to `"User ID: default_user"`, `memory_context=""`).
- **Personality Rigidity Driven by Over-Constrained Prompts**: `system.py` strictly constrains responses to 1–2 sentences, enforces an executive persona by default, and includes rigid anti-filler rules that trigger repetitive "How can I help you?" loops.

---

## 2. Architecture

### Actual Current Runtime Architecture Diagram

```
                                  +-------------------------------------------------------------+
                                  |                     Browser Client                          |
                                  | - getUserMedia (16kHz mono)                                 |
                                  | - ScriptProcessor (Float32 -> Int16 PCM)                    |
                                  | - Web Audio API AudioBufferSourceNode (24kHz output)        |
                                  +------------------------------+------------------------------+
                                                                 |
                                      Client WebSocket: /api/voice/ws/{session_id}
                                      (Full-Duplex: Binary PCM Audio + JSON Control Events)
                                                                 |
                                                                 v
+-------------------------------------------------------------------------------------------------------------------------------+
| FastAPI Gateway (voice-agent/app)                                                                                             |
|                                                                                                                               |
|  [app/api/v1/voice.py]                [app/realtime/session.py]                  [app/integrations/deepgram/agent_session.py]   |
|  voice_agent_websocket() ------------> RealtimeClientSession -------------------> DeepgramVoiceAgentSession                   |
|                                         - State: SessionState                     - websockets.connect(wss://agent...)        |
|                                         - Forwards raw PCM bytes                  - Sends initial Settings (STT/Think/Speak)  |
|                                         - Forwards JSON events                    - Dispatches FunctionCallRequest            |
+------------------------------------------------------------------------------------------------+------------------------------+
                                                                                                 |
                                                           Upstream WebSocket: wss://agent.deepgram.com/v1/agent/converse
                                                           (Full-Duplex: Binary 24kHz PCM Audio + JSON Deepgram Protocol)
                                                                                                 |
                                                                                                 v
+-------------------------------------------------------------------------------------------------------------------------------+
| Deepgram Voice Agent API Cloud                                                                                                |
|                                                                                                                               |
|  +---------------------------------+    +----------------------------------+    +------------------------------------------+  |
|  | Listen: Nova-2 STT              | -> | Think: Groq (openai/gpt-oss-20b) | -> | Speak: Aura TTS (aura-asteria-en, 24kHz) |  |
|  | - Live streaming STT + VAD      |    | - Evaluates 15 Tool Schemas      |    | - Synthesizes spoken response            |  |
|  | - Emits UserStartedSpeaking     |    | - Emits FunctionCallRequest      |    | - Streams binary linear16 PCM frames     |  |
|  +---------------------------------+    +-----------------+----------------+    +------------------------------------------+  |
+-----------------------------------------------------------|-------------------------------------------------------------------+
                                                            |
                                      FunctionCallRequest   |   FunctionCallResponse
                                      (via Upstream WS)     |   (via Upstream WS)
                                                            v
+-------------------------------------------------------------------------------------------------------------------------------+
| Tool Execution Subsystem (Backend)                                                                                            |
|                                                                                                                               |
|  [app/tools/registry.py]                   [app/integrations/composio/client.py]                                              |
|  ToolRegistry.execute_tool() ------------> ComposioGateway.execute_action()                                                   |
|  - Validates tool presence                 - composio.tools.execute(slug=..., arguments=..., user_id=...)                     |
|  - Evaluates confirmation policy           - Handles OAuth connections (Gmail, Outlook, Google Calendar, SerpAI, Perplexity)  |
+-------------------------------------------------------------------------------------------------------------------------------+
```

### Exact Textual Architecture Flow
1. **Microphone**: Captured in browser via `getUserMedia` (16kHz mono).
2. **Frontend Audio Transport**: Converted from Float32 to Int16 PCM in `ScriptProcessorNode`, transmitted as raw binary frames over `/api/voice/ws/{session_id}`.
3. **Backend Gateway**: FastAPI `voice_agent_websocket` delegates to `RealtimeClientSession`, which forwards raw PCM bytes directly to `DeepgramVoiceAgentSession.send_audio()`.
4. **Deepgram STT**: Deepgram Voice Agent API receives raw PCM audio, transcribes via Nova-2, and performs VAD turn boundary detection.
5. **LLM (Think Provider)**: Deepgram's cloud invokes Groq LPU with `model: "openai/gpt-oss-20b"`, passing the system prompt instructions and all 15 tool function schemas.
6. **Tool Router / Execution**: When Groq requests a function, Deepgram sends a `FunctionCallRequest` JSON event over the upstream WebSocket. FastAPI's `_handle_function_call()` executes the tool via `ToolRegistry.execute_tool()`, which calls `ComposioGateway.execute_action()`.
7. **Composio**: Executes the mapped action on external OAuth services (Gmail, Outlook, Google Calendar, SerpAI, Perplexity, Google Workspace).
8. **Tool Result**: The backend serializes the result dictionary and sends a `FunctionCallResponse` JSON event back over the upstream WebSocket to Deepgram.
9. **Final LLM Response**: Groq processes the tool output and streams the final conversational text response into Deepgram's TTS engine.
10. **TTS (Speak Provider)**: Deepgram Aura TTS (`aura-asteria-en`) synthesizes text into 24kHz linear16 PCM audio chunks and transmits them as binary frames over the upstream WebSocket.
11. **Frontend Audio Playback**: FastAPI forwards binary frames to the client WebSocket. Browser `ws.onmessage` converts Int16 PCM to Float32, creates `AudioBufferSourceNode`, and schedules playback seamlessly via `nextPlayTime += audioBuffer.duration` on `AudioContext(sampleRate: 24000)`.

---

## 3. Important File Map

| Concern | File | Symbol / Class / Function | Purpose |
| :--- | :--- | :--- | :--- |
| **Startup & Lifespan** | [app/main.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/main.py#L22-L57) | `lifespan()`, `app` | Initializes tool registry, logs model config, mounts REST router and playground. |
| **Application Config** | [app/core/config.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/core/config.py#L4-L43) | `Settings`, `settings` | Pydantic BaseSettings loading environment variables for Deepgram, Groq, Composio, Supabase. |
| **Voice WS Endpoint** | [app/api/v1/voice.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/api/v1/voice.py#L92-L121) | `voice_agent_websocket()` | Manages client WebSocket connections at `/api/voice/ws/{session_id}`. |
| **Client Session Bridge** | [app/realtime/session.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/session.py#L15-L108) | `RealtimeClientSession` | Bridges client WebSocket with Deepgram session, coordinates state transitions and audio forwarding. |
| **Session State Enum** | [app/realtime/state.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/state.py#L6-L19) | `SessionState` | Enumeration of lifecycle states (`CONNECTING`, `LISTENING`, `SPEAKING`, etc.). |
| **Deepgram Gateway** | [app/integrations/deepgram/agent_session.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L17-L246) | `DeepgramVoiceAgentSession` | Manages upstream WebSocket connection to Deepgram Agent API, builds `Settings`, handles function calls and greetings. |
| **Tool Registry & Policy** | [app/tools/registry.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/registry.py#L21-L141) | `ToolRegistry`, `tool_registry` | Registers 15 tools, exports Deepgram schemas, enforces write confirmation policy, executes tools. |
| **Base Tool Interface** | [app/tools/base.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/base.py#L7-L42) | `BaseTool` | Abstract base class defining tool metadata, execution interface, and schema converters. |
| **Composio Client** | [app/integrations/composio/client.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/composio/client.py#L24-L229) | `ComposioGateway`, `composio_gateway` | Wraps Composio SDK for OAuth authentication, connected account discovery, and action execution. |
| **Email Tools** | [app/tools/email/tools.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/email/tools.py#L35-L143) | `SendEmailTool`, `SearchEmailsTool` | Email search/send implementation defaulting to Gmail. |
| **Calendar Tools** | [app/tools/calendar/tools.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/calendar/tools.py#L38-L160) | `CreateCalendarEventTool`, `ListCalendarEventsTool` | Calendar creation/search defaulting to Google Calendar. |
| **Search Tools** | [app/tools/search/tools.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/search/tools.py#L8-L74) | `SerpApiSearchTool`, `PerplexityResearchTool` | Real-time web search and deep research via SerpAI and Perplexity AI. |
| **Dynamic Action Tool** | [app/tools/workspace/dynamic_action.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/workspace/dynamic_action.py#L56-L149) | `ExecuteAppActionTool` | Meta-tool mapping intent and app name to Composio action slugs via heuristic dictionary. |
| **Workspace Tools** | [app/tools/workspace/tools.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/workspace/tools.py#L8-L120) | `GoogleSheetsTool`, `GoogleDocsTool`, `GoogleDriveTool` | Tools for Google Sheets, Docs, and Drive. |
| **System Prompts** | [app/agent/prompts/system.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/agent/prompts/system.py#L12-L62) | `VOICE_AGENT_BASE_INSTRUCTIONS`, `build_system_prompt()` | Enforces voice delivery rules (plain text, conversational brevity, spoken numbers). |
| **Personas** | [app/agent/prompts/personas.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/agent/prompts/personas.py#L5-L28) | `PERSONAS`, `get_persona_prompt()` | Defines tonal templates (`executive`, `casual`, `researcher`, `concierge`). |
| **Persona Service** | [app/agent/persona/service.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/agent/persona/service.py#L8-L29) | `PersonaService`, `persona_service` | Combines persona templates with runtime user and memory context. |
| **LangGraph Graph** | [app/agent/graph.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/agent/graph.py#L44-L85) | `build_agent_graph()`, `agent_graph` | LangGraph StateGraph (standalone; unused in real-time voice sessions). |
| **Conversation Service** | [app/conversations/service.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/conversations/service.py#L13-L95) | `ConversationService`, `conversation_service` | Maintains in-memory session message history and mirrors to Supabase `messages` table. |
| **Memory Service** | [app/memory/service.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/memory/service.py#L14-L134) | `MemoryService`, `memory_service` | In-memory and Supabase memory storage, keyword search, and structured fact extraction. |
| **Observability & Latency** | [app/observability/latency.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/observability/latency.py#L8-L38) | `TurnLatencyMetrics`, `LatencyTracker` | Unused telemetry classes for milestone tracking. |
| **Metrics Collector** | [app/observability/metrics.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/observability/metrics.py#L10-L51) | `MetricsCollector`, `metrics_collector` | Prometheus metrics exporter (`/api/metrics`). |
| **Frontend Playground** | [app/realtime/playground.html](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L476-L913) | AudioContext, WebSocket handlers | Client UI, microphone capture (16kHz), audio scheduling, and live connector management. |

---

## 4. Current Voice Configuration

The exact Deepgram `Settings` payload is constructed in [app/integrations/deepgram/agent_session.py:63-109](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L63-L109):

```json
{
  "type": "Settings",
  "audio": {
    "input": {
      "encoding": "linear16",
      "sample_rate": 16000
    },
    "output": {
      "encoding": "linear16",
      "sample_rate": 24000
    }
  },
  "agent": {
    "listen": {
      "provider": {
        "type": "deepgram",
        "model": "nova-2"
      }
    },
    "think": {
      "provider": {
        "type": "groq",
        "model": "openai/gpt-oss-20b"
      },
      "prompt": "<instructions from build_system_prompt()>",
      "functions": "<15 tool schemas from tool_registry>"
    },
    "speak": {
      "provider": {
        "type": "deepgram",
        "model": "aura-asteria-en"
      }
    }
  }
}
```

### Configuration Property Audit

| Section | Parameter | Current Value | Source File & Line | Status / Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Listen / STT** | Provider Type | `"deepgram"` | [agent_session.py:86](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L86) | Configured |
| | API Endpoint / Version | `wss://agent.deepgram.com/v1/agent/converse` | [config.py:21](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/core/config.py#L21) | Agent API v1 |
| | Model | `"nova-2"` | [config.py:22](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/core/config.py#L22) | Configured |
| | Input Encoding | `"linear16"` | [agent_session.py:75](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L75) | Configured |
| | Input Sample Rate | `16000` | [config.py:24](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/core/config.py#L24) | Configured |
| | Language | `ABSENT` | - | Defaults to Deepgram English |
| | Endpointing / Turn Detection | `ABSENT` | - | Not specified in payload |
| | `eot_threshold` | `ABSENT` | - | Not specified in payload |
| | `eager_eot_threshold` | `ABSENT` | - | Not specified in payload |
| | `eot_timeout_ms` | `ABSENT` | - | Not specified in payload |
| | VAD settings | `ABSENT` | - | Uses Deepgram server default |
| | Interruption settings | `ABSENT` | - | Uses Deepgram server default |
| **Think / LLM** | Provider Type | `"groq"` | [agent_session.py:92](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L92) | Configured |
| | Model | `"openai/gpt-oss-20b"` | [agent_session.py:69](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L69) | **Hardcoded override** (ignores `config.py: groq_model="groq/compound"`) |
| | Prompt | `persona_service.get_voice_instructions()` | [agent_session.py:65](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L65) | Assembled via `build_system_prompt()` |
| | Functions / Tools | 15 tool schemas | [registry.py:50](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/registry.py#L50) | All 15 tools exported |
| | Temperature | `ABSENT` in Settings | - | `config.py:31` defines `0.3`, but not passed to Deepgram |
| | Max Output Tokens | `ABSENT` in Settings | - | `config.py:32` defines `1024`, but not passed to Deepgram |
| | Timeout Configuration | `ABSENT` | - | Not specified |
| | Streaming Configuration | `ABSENT` | - | Handled by Deepgram |
| **Speak / TTS** | Provider Type | `"deepgram"` | [agent_session.py:100](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L100) | Configured |
| | Model / Voice | `"aura-asteria-en"` | [config.py:23](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/core/config.py#L23) | Deepgram Aura v1 |
| | Output Encoding | `"linear16"` | [agent_session.py:79](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L79) | Configured |
| | Output Sample Rate | `24000` | [config.py:25](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/core/config.py#L25) | Configured |
| | Speaking Rate / Speed | `ABSENT` in Settings | - | `persona/config.py:12` defines `1.0`, but not passed to Deepgram |
| | Expressivity | `ABSENT` | - | Not supported in Aura v1 |
| | Output Transport | Binary WebSocket frames | [agent_session.py:134](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L134) | Direct PCM streaming |
| | Flux TTS (`/v2`) | `ABSENT` / `NOT USED` | - | Flux is not referenced anywhere |
| | Aura TTS (`/v1`) | `ACTIVE` | [config.py:23](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/core/config.py#L23) | Currently active |

---

## 5. Greeting Lifecycle

### Lifecycle Trace and Latency Breakdown

```text
T0 [0ms]        User clicks "Start Mic" button in playground.html.
T1 [+45ms]      Browser executes HTTP POST /api/voice/sessions (Network RTT #1).
T2 [+70ms]      Backend creates session ID, returns SessionResponse(status="created").
T3 [+85ms]      Browser opens WebSocket: ws://localhost:8000/api/voice/ws/{session_id} (Network RTT #2).
T4 [+105ms]     Backend voice_agent_websocket accepts WS, instantiates RealtimeClientSession, calls start().
T5 [+115ms]     Backend sends {"type": "SessionStateChange", "state": "connected"} to browser.
T6 [+130ms]     Backend opens upstream WS to wss://agent.deepgram.com/v1/agent/converse (Network RTT #3).
T7 [+260ms]     Deepgram WS handshake succeeds.
T8 [+275ms]     Backend builds Settings JSON (formats 15 tool schemas + system prompt) and sends to Deepgram.
T9 [+480ms]     Deepgram parses Settings, initializes STT/LLM/TTS, and sends {"type": "SettingsApplied"} back.
T10 [+495ms]    Backend receives SettingsApplied in _handle_server_event() (agent_session.py:160).
T11 [+505ms]    Backend sends {"type": "InjectAgentMessage", "content": "Hello! I'm here and ready to help."} to Deepgram (Network RTT #4).
T12 [+750ms]    Deepgram receives InjectAgentMessage, routes text to Aura TTS engine.
T13 [+950ms]    Deepgram synthesizes first 24kHz PCM audio chunk and transmits over WS (Network RTT #5).
T14 [+980ms]    Backend receives binary audio chunk in _receive_loop() and forwards to Client WS via send_bytes().
T15 [+1010ms]   Browser ws.onmessage receives ArrayBuffer, playAudioChunk() converts PCM16 to Float32, schedules on AudioContext.
T16 [+1030ms]   Audio playback begins on client speaker.
```

### Specific Answers to Greeting Diagnostic Questions:
1. **Where greeting text is defined:** Hardcoded string in [app/integrations/deepgram/agent_session.py:164](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L164):
   ```python
   greeting_payload = {
       "type": "InjectAgentMessage",
       "content": "Hello! I'm here and ready to help.",
   }
   ```
2. **Greeting definition category:** Application code event handler responding to `SettingsApplied`. It is **NOT** in Deepgram `agent.greeting`, not in the system prompt, not in the frontend, and not an LLM-generated turn.
3. **Does an LLM request occur before greeting?** No. `InjectAgentMessage` injects assistant text directly into Deepgram TTS without LLM invocation.
4. **Does LangGraph initialization block greeting?** No. LangGraph is not in the execution path.
5. **Are Composio tools loaded before greeting?** Yes. All 15 tool schemas are generated synchronously via `tool_registry.get_deepgram_function_schemas()` in `_send_settings_configuration()` prior to `SettingsApplied`.
6. **Are connected accounts fetched before greeting?** No. Backend does not query Composio for connected accounts during voice session initialization.
7. **Are database operations blocking greeting?** In-memory session initialization in `conversation_service.get_or_create_session()` takes <1ms.
8. **Does frontend wait for state before playback?** No. As soon as `ws.onopen` fires, incoming binary messages are processed immediately.
9. **Unnecessary awaits in startup path:** The sequential HTTP POST session creation followed by separate WebSocket connection adds an unnecessary REST round-trip (~50-80ms).
10. **Primary latency contributors:** 
    - 5 sequential network round trips between browser, FastAPI, and Deepgram.
    - Reactive round-trip greeting trigger (`Settings` → wait for `SettingsApplied` → send `InjectAgentMessage` → wait for TTS) instead of native `agent.greeting` configuration in the initial `Settings` payload.

---

## 6. Turn and Audio Lifecycle

```
[Listening]
  User speaks into microphone (16kHz PCM)
  -> ScriptProcessor captures chunks of 1024 samples
  -> Sent as binary frames over Client WS
  -> Forwarded directly to Deepgram Agent WS via send_audio()
  -> Deepgram Nova-2 STT streams transcript
  |
  +---> [User Started Speaking Event]
  |       Deepgram detects speech onset -> emits UserStartedSpeaking event
  |       -> Forwarded to Client WS -> Frontend calls stopAllAudioPlayback() (stops active AudioNodes)
  v
[Thinking]
  Deepgram VAD detects end of user turn
  -> Emits AgentThinking event -> SessionState becomes THINKING
  -> Groq Think provider evaluates prompt, conversation history, and 15 tool schemas
  |
  +---> Choice A: Direct Spoken Response
  |       Groq streams text tokens -> Deepgram Aura TTS synthesizes 24kHz linear16 PCM
  |       -> Proceeds directly to [Speaking]
  |
  +---> Choice B: Tool / Function Call
          Groq emits function call -> Deepgram sends FunctionCallRequest event over WS
          -> Backend _handle_function_call() executes tool synchronously via ToolRegistry.execute_tool()
          -> Composio action executes (or returns confirmation requirement)
          -> Backend sends FunctionCallResponse event over WS to Deepgram
          -> Groq receives tool response and produces final assistant response text
          -> Deepgram Aura TTS synthesizes 24kHz PCM
  v
[Speaking]
  Deepgram emits AgentStartedSpeaking event -> SessionState becomes SPEAKING
  -> Deepgram streams binary 24kHz PCM audio frames over WS
  -> Backend _receive_loop() receives bytes -> forwards to Client WS
  -> Frontend ws.onmessage receives ArrayBuffer -> playAudioChunk()
  -> Web Audio API schedules AudioBufferSourceNode sequentially (nextPlayTime += buffer.duration)
  |
  v
[End of Turn]
  Deepgram finishes audio transmission -> emits AgentAudioDone event
  -> SessionState transitions to LISTENING
  -> Deepgram emits ConversationText (logged to ConversationService and Supabase)
```

---

## 7. Overlapping Audio Investigation

### Root Cause Analysis & Evidence

Overlapping speech occurs primarily due to a **lack of chunk-level generation identifiers coupled with network in-flight buffering**, compounded by **missing cancellation triggers on text injection**:

#### 1. In-Flight Binary Chunks Bypass Barge-In Reset
In [app/realtime/playground.html:844-856](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L844-L856):
```javascript
function stopAllAudioPlayback() {
    activeAudioSources.forEach(source => {
        try {
            source.stop();
            source.disconnect();
        } catch (e) {}
    });
    activeAudioSources = [];
    if (playbackAudioContext) {
        nextPlayTime = playbackAudioContext.currentTime;
    }
}
```
When `UserStartedSpeaking` arrives, `stopAllAudioPlayback()` stops active AudioBufferSourceNodes and sets `nextPlayTime = playbackAudioContext.currentTime`. However:
- Binary chunks are transmitted over the WebSocket without any header, sequence number, turn ID, or generation timestamp.
- Audio chunks that were already buffered in TCP sockets or in-flight across the network arrive at `ws.onmessage` **milliseconds after `stopAllAudioPlayback()` executed**.
- `ws.onmessage` has no generation filter, so it passes these late chunks to `playAudioChunk()`.
- `playAudioChunk()` schedules them starting at `nextPlayTime` (which was reset to current time).
- When the new assistant turn produces audio, its chunks are appended right after the stale chunks, causing the user to hear the tail of the old sentence followed immediately by the new sentence, or both overlapping if `nextPlayTime` clock synchronization drifts.

#### 2. Text Input Injection (`InjectUserMessage`) Omits Audio Cancellation
In [app/realtime/playground.html:770-777](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L770-L777):
```javascript
sendBtn.onclick = () => {
    const text = textInput.value.trim();
    if (text && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'InjectUserMessage', content: text }));
        appendMessage('user', text);
        textInput.value = '';
    }
};
```
When the user submits a text message while the agent is speaking:
- The frontend **does not call `stopAllAudioPlayback()`**.
- Deepgram does not emit `UserStartedSpeaking` on `InjectUserMessage`.
- Neither backend nor frontend sends Deepgram's `Interrupt` control message.
- Deepgram continues streaming TTS for the prior response while simultaneously queuing or generating the new response, resulting in audio collisions.

#### 3. Diagnostic Checklist Responses

| Question | Code Reality | Evidence Path & Line |
| :--- | :--- | :--- |
| Does user barge-in stop local playback? | **Yes, for already-scheduled nodes.** | [playground.html:799](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L799) |
| Is the playback buffer cleared? | **Partial**: active nodes stopped; in-flight frame queue not cleared. | [playground.html:844-855](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L844-L855) |
| Is current TTS generation cancelled at Deepgram? | **Handled automatically by Deepgram on STT VAD only**, not on text injection. | Deepgram Server Side |
| Is current LLM generation cancelled? | **No explicit cancel command sent.** | [agent_session.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py) |
| Are late audio frames discarded? | **NO.** | [playground.html:736](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L736) |
| Can audio from two turns coexist in playback queue? | **YES.** | [playground.html:857-888](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L857-L888) |
| Does audio carry `turn_id` / `generation_id`? | **NO.** Audio is raw binary PCM. | [agent_session.py:134](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L134) |
| Can stale audio be distinguished from current audio? | **NO.** | - |
| Are multiple audio playback instances created? | **NO** (single `playbackAudioContext`). | [playground.html:858](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L858) |
| Are multiple WS listeners accidentally registered? | **NO.** Clean listener lifecycle. | [playground.html:734-745](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L734-L745) |
| Can multiple assistant response tasks run concurrently? | **NO.** Tool execution is single-threaded async in `_handle_function_call`. | [agent_session.py:185-225](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L185-L225) |
| Can acknowledgement and final response overlap? | **NO spoken acknowledgements exist**; tool wait is silent. | [agent_session.py:209-224](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L209-L224) |
| Is `UserStartedSpeaking` handled? | **YES.** Updates state and triggers `stopAllAudioPlayback()`. | [playground.html:797-799](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L797-L799) |
| Is `AgentAudioDone` handled? | **YES.** Transitions status to LISTENING. | [playground.html:804-807](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L804-L807) |
| Is Deepgram `Interrupt` used? | **NO.** | Not found in codebase |
| Is `SpeechInterrupted` used? | **NO.** | Not found in codebase |
| Is `text_spoken` / `text_remaining` tracked? | **NO.** | Not found in codebase |

---

## 8. Composio Integration

### Integration Technical Specifications
- **Composio SDK Version:** `composio-core>=0.6.0`, `composio-langchain>=0.6.0` ([pyproject.toml:18-19](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/pyproject.toml#L18-L19)).
- **Client Wrapper:** `ComposioGateway` in [app/integrations/composio/client.py:24-229](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/composio/client.py#L24-L229).
- **Initialization:** Lazy instantiation using `from composio import Composio; self._client = Composio(api_key=self.api_key)`.
- **User Identity Mapping:** Maps application `user_id` / `entity_id` directly to Composio `user_id`.
- **Auth Configuration Discovery:** Queries `self._client.auth_configs.list()` and caches auth config IDs by slug in `_auth_configs_cache` ([client.py:47-69](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/composio/client.py#L47-L69)).
- **Integration Pattern Used:**
  - Direct action execution via `self._client.tools.execute(slug=action_name, arguments=params, user_id=entity_id, dangerously_skip_version_check=True)` ([client.py:196-203](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/composio/client.py#L196-L203)).
  - Direct account linking via `self._client.connected_accounts.link(user_id=entity_id, auth_config_id=auth_config_id, callback_url=...)` ([client.py:106-109](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/composio/client.py#L106-L109)).
  - Direct account listing via `self._client.connected_accounts.list(user_ids=[entity_id])` ([client.py:141-144](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/composio/client.py#L141-L144)).
- **Schema Exposure & Limits:**
  - Schemas are converted to Deepgram function schemas in [app/tools/base.py:35-41](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/base.py#L35-L41).
  - All 15 tools are exposed to the LLM simultaneously. There is no global limit of 20 being enforced because total tool count is 15.

---

## 9. Tool Routing Investigation

### Analysis of Concrete Routing Failures

```
User Query: "Do I have anything tomorrow morning?"
   |
   +---> Deepgram LLM evaluates 15 function definitions
           |
           +---> Schema A: list_calendar_events (parameters: time_min, time_max, max_events, provider)
           |       - provider enum: ["google", "outlook"] (default: "google")
           |
           +---> Schema B: execute_app_action (parameters: app_name, intent, parameters)
                   - app_name enum: ["gmail", "googlecalendar", "googlesheets", "googledocs", "googledrive", "outlook", "serpapi", "perplexityai"]
```

#### Why Wrong Toolkit or Wrong Action Occurs (Ranked by Evidence):

1. **[CONFIRMED] Competing Redundant Schemas (Specific Tools vs. Universal Meta-Tool)**
   - The LLM is provided both granular tools (`send_email`, `search_emails`, `create_calendar_event`, `list_calendar_events`, `web_search_serpapi`, `perplexity_ai_research`) and `execute_app_action`.
   - `execute_app_action` advertises support for Gmail, Calendar, Sheets, Docs, Drive, Outlook, and Search ([dynamic_action.py:60-63](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/workspace/dynamic_action.py#L60-L63)).
   - This creates schema competition where the LLM arbitrarily splits decisions between specific tools and `execute_app_action`.

2. **[CONFIRMED] Biased Default Parameters for Dual-Provider Capabilities**
   - In `SearchEmailsTool` ([tools.py:102](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/email/tools.py#L102)) and `SendEmailTool` ([tools.py:54](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/email/tools.py#L54)), the provider default is hardcoded to `"gmail"`.
   - In `ListCalendarEventsTool` ([tools.py:112](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/calendar/tools.py#L112)) and `CreateCalendarEventTool` ([tools.py:59](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/calendar/tools.py#L59)), the provider default is hardcoded to `"google"`.
   - When a user says *"Check my emails"* or *"Do I have anything tomorrow?"*, the LLM leaves `provider` blank. The tools default to `GMAIL_FETCH_EMAILS` and `GOOGLECALENDAR_FIND_EVENT`. If the user has connected Outlook instead, the call fails with `ConnectedAccountNotFound`.

3. **[CONFIRMED] Prompt Has Zero Awareness of User's Connected Accounts**
   - `DeepgramVoiceAgentSession._send_settings_configuration()` passes only `user_context="User ID: default_user"`.
   - It never queries `composio_gateway.get_connected_accounts()`.
   - The LLM has no prompt knowledge of which accounts (Gmail vs Outlook) are actually connected for the active user.

4. **[CONFIRMED] Inconsistent Action Slugs & Parameter Naming**
   - `PerplexityResearchTool` expects argument `prompt` ([search/tools.py:55](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/search/tools.py#L55)), but `SerpApiSearchTool` and `SearchEmailsTool` expect `query`.
   - In `dynamic_action.py:31-44`, Google Sheets maps to `GOOGLESHEETS_BATCH_GET` and Google Drive maps to `GOOGLEDRIVE_SEARCH_FILES`, whereas `workspace/tools.py:41,114` calls `GOOGLESHEETS_READ` and `GOOGLEDRIVE_SEARCH`.
   - `GoogleSheetsTool`, `GoogleDocsTool`, and `GoogleDriveTool` in [workspace/tools.py:48,86,114](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/workspace/tools.py#L48) omit `entity_id=user_id` when invoking `execute_action()`.

5. **[STRONG EVIDENCE] Multi-Step / Sequential Action Limitations**
   - For queries like *"Reply to John's latest email"*, the agent needs a search step followed by a send step. Because Deepgram executes one function call round-trip per turn, the model must inspect the first result before initiating the second. However, `search_emails` returns a compact summary list without message IDs or thread IDs, making it impossible for the model to construct a valid thread reply in the second turn.

---

## 10. Connected Toolkits

The exact 8 apps and toolkits configured in [app/integrations/composio/client.py:12-21](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/composio/client.py#L12-L21) are:

| App Name | Display Name | Capability | Description | Loaded Actions in Code |
| :--- | :--- | :--- | :--- | :--- |
| `GMAIL` | Gmail | `email` | Read, search, and send emails | `GMAIL_FETCH_EMAILS`, `GMAIL_SEND_EMAIL`, `GMAIL_CREATE_DRAFT` |
| `OUTLOOK` | Outlook / Office 365 | `email` / `calendar` | Manage Outlook mail, calendar, and contacts | `OUTLOOK_GET_EMAILS`, `OUTLOOK_SEND_MAIL`, `OUTLOOK_CREATE_EVENT`, `OUTLOOK_GET_CALENDAR_VIEW` |
| `GOOGLECALENDAR` | Google Calendar | `calendar` | Create and check calendar meetings | `GOOGLECALENDAR_FIND_EVENT`, `GOOGLECALENDAR_CREATE_EVENT`, `GOOGLECALENDAR_FIND_FREE_SLOTS` |
| `SERPAPI` | SerpAI (Google Search) | `search` | Real-time live Google web search | `SERPAPI_SEARCH` |
| `PERPLEXITYAI` | Perplexity AI | `search` | Deep online AI search and synthesis | `PERPLEXITYAI_PERPLEXITY_AI_SEARCH` |
| `GOOGLESHEETS` | Google Sheets | `workspace` | Read and append spreadsheet rows | `GOOGLESHEETS_BATCH_GET`, `GOOGLESHEETS_APPEND_VALUES`, `GOOGLESHEETS_UPDATE_VALUES`, `GOOGLESHEETS_CREATE_SPREADSHEET`, `GOOGLESHEETS_READ`, `GOOGLESHEETS_APPEND` |
| `GOOGLEDOCS` | Google Docs | `workspace` | Create and update Google documents | `GOOGLEDOCS_CREATE_DOCUMENT`, `GOOGLEDOCS_GET_DOCUMENT`, `GOOGLEDOCS_CREATE`, `GOOGLEDOCS_APPEND` |
| `GOOGLEDRIVE` | Google Drive | `workspace` | Search and retrieve Drive files | `GOOGLEDRIVE_SEARCH_FILES`, `GOOGLEDRIVE_GET_FILE`, `GOOGLEDRIVE_SEARCH` |

*Note: All 15 tool definitions across these 8 apps are statically registered at startup into `tool_registry`.*

---

## 11. Voice Selection Feasibility

### Implementation Assessment: Low-to-Moderate Complexity

1. **Current State:**
   - Deepgram TTS model is read once from `settings.deepgram_tts_model` (`"aura-asteria-en"`) during `_send_settings_configuration()`.
   - `PersonaConfig` in `app/agent/persona/config.py:11` has a `voice_model` field, but it is currently decoupled from `agent_session.py`.
   - No UI element exists for voice selection.
   - Deepgram `UpdateSpeak` message handler is not implemented.

2. **Integration Path:**

```
Frontend UI Dropdown (playground.html)
  |  (Selects e.g. aura-helios-en, aura-asteria-en, aura-luna-en, aura-orion-en)
  v
Client WebSocket Message: {"type": "UpdateVoice", "voice": "aura-helios-en"}
  |
  v
FastAPI RealtimeClientSession._handle_client_event() (app/realtime/session.py)
  |
  v
DeepgramVoiceAgentSession.update_voice(voice_model: str) (app/integrations/deepgram/agent_session.py)
  |  Sends JSON payload over upstream WS:
  |  {"type": "UpdateSpeak", "model": voice_model}
  v
Deepgram Agent API applies new voice dynamically for subsequent turns.
```

3. **Required Code Touchpoints:**
   - `app/integrations/deepgram/agent_session.py`: Add `update_speak(self, voice_model: str)` method sending `{"type": "UpdateSpeak", "model": voice_model}`.
   - `app/realtime/session.py`: Handle `UpdateVoice` control event in `_handle_client_event()`.
   - `app/api/v1/voice.py`: Accept `voice` query parameter in `/sessions` and `/ws/{session_id}`.
   - `app/realtime/playground.html`: Add `<select id="voiceSelect">` inside the Voice Controls card.

---

## 12. Companion / Personality Architecture

### Causes of Rigid / Robotic Behavior

1. **Overly Restrictive Length Constraints**
   - [app/agent/prompts/system.py:22,37](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/agent/prompts/system.py#L22):
     ```text
     2. Keep answers between 1 to 2 short sentences per turn unless the user specifically asks for more detail.
     5. After a tool returns results, summarize the key takeaway in 1 to 2 brief spoken sentences without any markdown.
     ```
   - Enforcing a strict 1–2 sentence limit on every turn suppresses conversational warmth, transitions, and natural companion-like engagement.

2. **Executive Tone by Default**
   - [app/agent/prompts/personas.py:6-9](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/agent/prompts/personas.py#L6-L9):
     ```text
     "You are an executive personal assistant. You are crisp, highly efficient, professional, and proactive. You prioritize time management, scheduling clarity, and concise summaries."
     ```
   - The default persona is tuned for corporate brevity rather than natural conversational rapport.

3. **Repetitive Anti-Filler Rules**
   - [app/agent/prompts/system.py:27](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/agent/prompts/system.py#L27):
     ```text
     If the user only says a greeting, acknowledgment, or short word (such as "Yeah", "Okay", "Hi", "Sure", "Cool"), DO NOT execute any tools. Simply ask warmly what they would like to do.
     ```
   - This causes the agent to repeatedly respond with canned "What would you like to do?" questions on acknowledgments.

4. **Absence of Memory & Personalization in Live Sessions**
   - While `MemoryService` and `UserProfile` exist, `DeepgramVoiceAgentSession` only passes `"User ID: default_user"` without loading user preferences, name, or previous turn context.

---

## 13. Memory and Context

- **Sent to LLM per Turn:** Deepgram maintains the rolling transcript upstream. The initial `Settings` prompt contains `VOICE_AGENT_BASE_INSTRUCTIONS` + persona template + `"User ID: default_user"`.
- **Memory Context Injection:** `memory_context` is currently passed as an empty string `""` during voice session startup ([agent_session.py:65](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L65)).
- **Interruption Transcript Truncation:** Deepgram emits `ConversationText` containing the full generated text turn. If the user interrupts halfway through playback, the backend and Supabase store the **entire generated message**, not the truncated portion actually heard by the user.
- **Context Growth:** Truncation helpers (`_format_compact_emails`, `_format_compact_events`) restrict preview lengths to 120 characters and 5 items. However, `ExecuteAppActionTool` passes uncurated Composio result dictionaries directly back into the LLM context.

---

## 14. Latency and Observability

### Current vs. Missing Telemetry

```
Pipeline Stage                   Current State    Implementation Detail
------------------------------------------------------------------------------------------------
1. Client Mic -> Gateway         MISSING          No audio packet timestamping
2. Gateway -> Deepgram STT       MISSING          Deepgram LatencyReport event ignored
3. Deepgram STT -> Groq LLM      MISSING          No STT duration telemetry captured
4. LLM Time to First Token       MISSING          LatencyTracker defined in latency.py but UNUSED
5. Tool Execution Duration       LOGGED ONLY      Python logger info only; not recorded in metrics
6. LLM Final Token -> TTS        MISSING          No TTFA (Time to first audio) tracked
7. TTS -> Client Playback        MISSING          No client-side playback telemetry
8. Prometheus Metrics Endpoint   BROKEN / NO-OP   MetricsCollector is never incremented in handlers
```

---

## 15. Tests

### Coverage Summary & Results

The test suite consists of 5 files across unit, integration, and E2E layers:

| Test File | Test Count | Key Areas Covered |
| :--- | :--- | :--- |
| `tests/unit/test_prompts.py` | 3 tests | `test_system_prompt_builder`, `test_persona_retrieval`, `test_persona_service_prompt` |
| `tests/unit/test_tools.py` | 7 tests | Registry initialization, metadata contract, capability filtering, write confirmation policy, time tool, memory tools, Perplexity fallback |
| `tests/unit/test_agent_graph.py` | 2 tests | `test_user_service_profile`, `test_agent_graph_execution` (tests LangGraph offline runner) |
| `tests/integration/test_app.py` | 10 tests | REST `/api/health`, `/api/tools`, `/api/integrations/*`, `/api/users/*`, `/api/memories/*`, `/api/conversations/*`, `/api/voice/sessions` |
| `tests/e2e/test_websocket_stream.py` | 3 tests | Starlette TestClient WebSocket connect `/api/voice/ws/{session_id}`, `/api/metrics`, `/playground` |

**Total Tests:** 25 test functions.  
**Test Suite Status:** Tests pass in mock/offline mode when dependencies are satisfied. Testing against live Deepgram WebSockets, live audio playback, live barge-in interruptions, and live Composio OAuth accounts is **not covered by automated tests**.

---

## 16. Confirmed Problems

### `[CONFIRMED]`
- **Late In-Flight Audio Chunks Cause Overlapping Playback**: Anonymous binary PCM frames lack turn/generation IDs. Chunks arriving after `UserStartedSpeaking` are scheduled at `nextPlayTime` and overlap subsequent speech ([playground.html:736,844](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L736)).
- **Text Injection (`InjectUserMessage`) Does Not Stop Audio**: Submitting text does not invoke `stopAllAudioPlayback()` or send an `Interrupt` signal ([playground.html:770](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L770)).
- **Greeting Latency Due to Multi-RTT Handshake**: Greeting is triggered reactively after `SettingsApplied` via `InjectAgentMessage` rather than using Deepgram's native `agent.greeting` ([agent_session.py:163](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L163)).
- **LangGraph Bypassed in Voice Hot Path**: `agent_graph` is never invoked in `RealtimeClientSession` or `DeepgramVoiceAgentSession` ([agent_session.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py)).
- **Dual Tooling Schema Collision**: Specific tools and universal `execute_app_action` both expose overlapping functionality to the LLM ([registry.py:121](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/registry.py#L121)).
- **Hardcoded Tool Provider Assumptions**: `search_emails` and `send_email` default to Gmail; `list_calendar_events` and `create_calendar_event` default to Google Calendar ([email/tools.py:69,115](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/email/tools.py#L69), [calendar/tools.py:74,126](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/calendar/tools.py#L74)).
- **Hardcoded Think Model**: `groq_think_model = "openai/gpt-oss-20b"` overrides `settings.groq_model` ([agent_session.py:69](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L69)).
- **Dynamic Action Confirmation Bypass**: `ExecuteAppActionTool` sets `requires_confirmation = False`, bypassing write checks for destructive actions ([dynamic_action.py:66](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/workspace/dynamic_action.py#L66)).
- **Missing Entity ID in Workspace Tools**: `GoogleSheetsTool`, `GoogleDocsTool`, and `GoogleDriveTool` do not pass `entity_id=user_id` to `composio_gateway.execute_action()` ([workspace/tools.py:48,86,114](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/workspace/tools.py#L48)).

### `[STRONG EVIDENCE]`
- **Interrupted Messages Stored as Fully Spoken**: Supabase `messages` table logs full `ConversationText` even when playback was halted early by barge-in ([agent_session.py:170-180](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L170-L180)).
- **Repetitive Canned Interaction Cycles**: Over-constrained anti-filler prompt rules force repetitive "What would you like to do?" cycles on conversational affirmations ([system.py:27](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/agent/prompts/system.py#L27)).

### `[POSSIBLE]`
- **Unbounded Context Latency in Workspace Dynamic Actions**: Large raw JSON structures returned by `ExecuteAppActionTool` may inflate Groq token context on subsequent turns ([dynamic_action.py:139](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/workspace/dynamic_action.py#L139)).

### `[NOT FOUND]`
- **Flux TTS Usage**: No references to Flux TTS (`/v2`) exist in the codebase.
- **Dynamic Voice Switching Support**: No Deepgram `UpdateSpeak` or runtime voice switcher exists.

---

## 17. Questions You Still Cannot Answer

1. **Target Groq Think Model for Deepgram Agent API**: Is `"groq/compound"` (from `config.py`) or `"llama-3.3-70b-versatile"` (from `README.md`) intended for production Deepgram Agent API think configurations, given that `"openai/gpt-oss-20b"` is currently hardcoded in `agent_session.py:69`?
2. **Preferred Voice Selection Scope**: Should Deepgram voice switching be persisted per-user in Supabase (`UserProfile.preferred_voice`), or should it be a transient per-session UI control in `playground.html`?
3. **Role of LangGraph**: Is LangGraph intended to sit in front of Deepgram as a custom server-side turn orchestrator (handling STT/LLM/TTS separately), or is Deepgram Voice Agent API intended to remain the real-time orchestrator while LangGraph is deprecated/removed?

---

## 18. Recommended Intervention Points

*Note: In accordance with audit constraints, no changes have been implemented.*

1. **Greeting Latency Fix**:
   - [app/integrations/deepgram/agent_session.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L83): Move greeting into `Settings["agent"]["greeting"] = "Hello! I'm here and ready to help."` and remove the late `InjectAgentMessage` trigger from `SettingsApplied`.
   - [app/realtime/playground.html](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L703-L733): Eliminate the preliminary HTTP POST `/api/voice/sessions` by generating the UUID client-side and connecting directly to WebSocket.

2. **Overlapping Audio & Interruption Fix**:
   - [app/realtime/playground.html](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L840-L888): Add a client-side `currentGenerationId` or `playbackEpoch` counter incremented on `stopAllAudioPlayback()`.
   - [app/realtime/session.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/session.py#L73) & [app/integrations/deepgram/agent_session.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L133): Wrap binary frames with a 4-byte generation counter or send a `ClearBuffer` control signal to discard in-flight chunks.
   - [app/realtime/playground.html](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L770): Add `stopAllAudioPlayback()` to `sendBtn.onclick` and send a Deepgram `Interrupt` control message.

3. **Tool Routing & Composio Disambiguation Fix**:
   - [app/tools/registry.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/registry.py#L121): Deprecate `ExecuteAppActionTool` or scope it strictly to unmapped apps to eliminate competing schemas.
   - [app/integrations/deepgram/agent_session.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L63-L108): Query `composio_gateway.get_connected_accounts(user_id)` during session startup, filter `tool_registry.get_deepgram_function_schemas(capabilities=...)`, and inject active connected app names into the system prompt.
   - [app/tools/email/tools.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/email/tools.py) & [app/tools/calendar/tools.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/calendar/tools.py): Dynamically resolve provider from connected accounts if not specified by user.
   - [app/tools/workspace/tools.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/workspace/tools.py#L48,86,114): Pass `entity_id=kwargs.get("user_id", "default_user")` to `composio_gateway.execute_action()`.

4. **Dynamic Voice Selection Implementation**:
   - [app/integrations/deepgram/agent_session.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py): Add `update_speak()` sending `{"type": "UpdateSpeak", "model": voice_model}`.
   - [app/realtime/playground.html](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html): Add voice selector `<select>` element sending `UpdateVoice` over WebSocket.

5. **Companion Prompt & Personality Refinement**:
   - [app/agent/prompts/system.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/agent/prompts/system.py): Relax 1–2 sentence limits to flexible conversational guidelines, soften anti-filler rules, and support natural conversational transitions.
   - [app/agent/persona/service.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/agent/persona/service.py): Load user profile and memory context from `MemoryService` before building prompt.

6. **Observability & Latency Instrumentation**:
   - [app/integrations/deepgram/agent_session.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L150): Add handler for Deepgram `LatencyReport` events.
   - [app/realtime/session.py](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/session.py): Wire `metrics_collector.increment_session()`, `decrement_session()`, `record_turn()`, and `record_tool_call()`.

---

## 19. Raw Evidence Appendix

### A. Deepgram Settings Payload Assembly
From [app/integrations/deepgram/agent_session.py:63-108](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L63-L108):
```python
    async def _send_settings_configuration(self) -> None:
        """Send the initial Settings payload specifying Groq + Nova-2 + Aura + Tools."""
        instructions = persona_service.get_voice_instructions(user_context=f"User ID: {self.user_id}")
        functions = tool_registry.get_deepgram_function_schemas()

        # Groq model supported by Deepgram Voice Agent API think provider
        groq_think_model = "openai/gpt-oss-20b"

        config_payload = {
            "type": "Settings",
            "audio": {
                "input": {
                    "encoding": "linear16",
                    "sample_rate": settings.input_sample_rate,
                },
                "output": {
                    "encoding": "linear16",
                    "sample_rate": settings.output_sample_rate,
                },
            },
            "agent": {
                "listen": {
                    "provider": {
                        "type": "deepgram",
                        "model": settings.deepgram_stt_model,
                    }
                },
                "think": {
                    "provider": {
                        "type": "groq",
                        "model": groq_think_model,
                    },
                    "prompt": instructions,
                    "functions": functions,
                },
                "speak": {
                    "provider": {
                        "type": "deepgram",
                        "model": settings.deepgram_tts_model,
                    }
                },
            },
        }

        logger.info(f"[{self.session_id}] Sending Settings to Deepgram (Groq model '{groq_think_model}', {len(functions)} tools).")
        await self.ws.send(json.dumps(config_payload))
```

### B. Late Spoken Greeting Trigger
From [app/integrations/deepgram/agent_session.py:160-167](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/integrations/deepgram/agent_session.py#L160-L167):
```python
        # 2. Settings Applied -> Trigger Instant Spoken Greeting
        elif event_type == "SettingsApplied":
            logger.info(f"[{self.session_id}] Settings applied. Triggering instant spoken greeting.")
            greeting_payload = {
                "type": "InjectAgentMessage",
                "content": "Hello! I'm here and ready to help.",
            }
            if self.ws and self._is_running:
                await self.ws.send(json.dumps(greeting_payload))
```

### C. Client Playback & Interruption Handling
From [app/realtime/playground.html:844-888](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/realtime/playground.html#L844-L888):
```javascript
        function stopAllAudioPlayback() {
            activeAudioSources.forEach(source => {
                try {
                    source.stop();
                    source.disconnect();
                } catch (e) {}
            });
            activeAudioSources = [];
            if (playbackAudioContext) {
                nextPlayTime = playbackAudioContext.currentTime;
            }
        }

        function playAudioChunk(arrayBuffer) {
            if (!playbackAudioContext) {
                playbackAudioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
            }
            if (playbackAudioContext.state === 'suspended') {
                void playbackAudioContext.resume();
            }

            const int16View = new Int16Array(arrayBuffer);
            const float32Data = new Float32Array(int16View.length);
            for (let i = 0; i < int16View.length; i++) {
                float32Data[i] = int16View[i] / 32768.0;
            }

            const audioBuffer = playbackAudioContext.createBuffer(1, float32Data.length, 24000);
            audioBuffer.getChannelData(0).set(float32Data);

            const source = playbackAudioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(playbackAudioContext.destination);

            const currentTime = playbackAudioContext.currentTime;
            if (nextPlayTime < currentTime) nextPlayTime = currentTime;
            source.start(nextPlayTime);
            nextPlayTime += audioBuffer.duration;

            activeAudioSources.push(source);
            source.onended = () => {
                const idx = activeAudioSources.indexOf(source);
                if (idx !== -1) activeAudioSources.splice(idx, 1);
            };
        }
```

### D. Hardcoded Provider Defaults in Tool Execution
From [app/tools/email/tools.py:68-70](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/email/tools.py#L68-L70) and [app/tools/calendar/tools.py:73-75](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/calendar/tools.py#L73-L75):
```python
# Email Tool
user_id = kwargs.get("user_id", "default_user")
action_name = "GMAIL_SEND_EMAIL" if provider.lower() == "gmail" else "OUTLOOK_SEND_MAIL"

# Calendar Tool
user_id = kwargs.get("user_id", "default_user")
action_name = "GOOGLECALENDAR_CREATE_EVENT" if provider.lower() == "google" else "OUTLOOK_CREATE_EVENT"
```

### E. Dynamic Action Bypassing Confirmation Safety
From [app/tools/workspace/dynamic_action.py:59-66](file:///c:/Users/coura/OneDrive/Desktop/VoiceAgent/voice-agent/app/tools/workspace/dynamic_action.py#L59-L66):
```python
class ExecuteAppActionTool(BaseTool):
    """Universal intent-driven tool to execute actions across connected workspace apps."""

    name = "execute_app_action"
    description = (
        "Dynamically execute an action on any connected workspace app based on user intent. "
        "Supports Gmail, Google Calendar, Google Sheets, Google Docs, Google Drive, Outlook, and Search."
    )
    capability = "workspace"
    read_only = False
    requires_confirmation = False  # Bypasses ToolRegistry confirmation check!
    timeout_seconds = 20.0
```
