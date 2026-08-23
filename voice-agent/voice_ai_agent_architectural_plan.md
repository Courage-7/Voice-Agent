# Voice AI Agent — Architectural Plan

## 1. Architectural Decision

Use a **feature-oriented modular monolith** with **ports/adapters around external systems** and a **small shared infrastructure layer**.

This gives the codebase:

- feature ownership;
- strong internal boundaries;
- one deployable FastAPI application;
- low operational complexity;
- replaceable vendor integrations;
- straightforward testing;
- a clean path to future service extraction only when scale or ownership justifies it.

Do **not** begin with:

- a purely technical/layered structure built only around `services/`, `repositories/`, `controllers/`, `models/`, and `utils/`;
- microservices;
- a giant generic `utils/` package;
- vendor SDK calls scattered through LangGraph nodes;
- strict textbook Clean Architecture ceremony for every tiny component.

The recommended architecture is:

```text
Feature-oriented modular monolith
        +
Ports/adapters around external systems
        +
Shared infrastructure only where genuinely cross-cutting
```

---

## 2. Why Not Purely Module/Layer-Based Architecture?

A purely layer-based structure often starts like this:

```text
services/
repositories/
models/
utils/
controllers/
schemas/
```

This looks clean initially, but a single business capability becomes fragmented across many directories.

For example, changing calendar behavior may require editing:

```text
controllers/calendar.py
services/calendar.py
repositories/calendar.py
schemas/calendar.py
models/calendar.py
```

The system is grouped by technical role rather than by product behavior.

That becomes increasingly painful as the agent gains:

- Gmail;
- Calendar;
- memory;
- user preferences;
- permissions;
- actions;
- tool routing;
- persona behavior;
- integration-specific policies.

A feature-oriented structure keeps related behavior close together.

---

## 3. Why Not Microservices Yet?

The MVP should remain a **modular monolith**.

The deployment unit is still:

```text
FastAPI application
```

Internally, however, modules have explicit boundaries.

Microservices would introduce unnecessary complexity:

- inter-service networking;
- distributed tracing;
- service discovery;
- multiple deployments;
- message brokers;
- versioned service contracts;
- distributed failure handling;
- operational overhead.

None of that is required to prove the first real-time voice-agent loop.

Possible future extraction candidates include:

- real-time audio gateway;
- tool execution service;
- memory service;
- analytics/observability pipeline.

But they should start inside one codebase.

---

## 4. Architectural Style

The architecture should combine four ideas.

### 4.1 Feature-Oriented Organization

Group product capabilities together.

Examples:

```text
realtime/
voice/
agent/
tools/
memory/
conversations/
users/
```

Each capability owns its behavior.

### 4.2 Ports and Adapters

External systems should be accessed through abstractions.

Example:

```text
CalendarService
      ↓
CalendarGateway
      ↓
ComposioCalendarGateway
      ↓
Composio SDK
```

The domain understands calendars.

The integration layer understands Composio.

These are separate responsibilities.

### 4.3 Dependency Inversion at External Boundaries

Internal business logic should not depend directly on:

- Deepgram;
- Supabase;
- Composio;
- a specific LLM vendor;
- Google Calendar;
- Gmail SDKs.

Internal modules depend on interfaces/protocols.

Concrete adapters implement those protocols.

### 4.4 Modular Monolith

All modules run in the same FastAPI process initially.

The architecture is modular internally without requiring a distributed system.

---

## 5. High-Level Dependency Direction

Desired dependency flow:

```text
realtime
   ↓
agent
   ↓
tools / memory / conversations
   ↓
ports / interfaces
   ↓
integrations
```

Avoid this:

```text
agent → Deepgram
agent → Supabase
agent → Composio
agent → Google SDK
agent → random vendor helpers
```

The agent should orchestrate application behavior, not become the integration layer.

---

## 6. Core Feature Areas / Bounded Contexts

| Module | Responsibility |
|---|---|
| `realtime` | WebSockets, event protocol, session lifecycle |
| `voice` | STT, TTS, VAD, endpointing, interruption handling |
| `agent` | LangGraph orchestration, state, reasoning, tool decisions |
| `tools` | Tool definitions, registry, grouping, routing |
| `memory` | Long-term memory storage and retrieval |
| `conversations` | Sessions and message persistence |
| `users` | User profile and application-level identity state |
| `integrations` | Deepgram, Composio, Supabase, LLM adapters |
| `observability` | Metrics, tracing, latency, structured logs |
| `core` | Configuration, dependency wiring, shared exceptions |

---

## 7. Recommended Repository Structure

```text
voice-agent/
├── app/
│   ├── main.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   │
│   ├── realtime/
│   │   ├── router.py
│   │   ├── websocket.py
│   │   ├── protocol.py
│   │   ├── session.py
│   │   ├── state.py
│   │   └── events.py
│   │
│   ├── voice/
│   │   ├── stt/
│   │   │   ├── service.py
│   │   │   ├── models.py
│   │   │   └── ports.py
│   │   │
│   │   ├── tts/
│   │   │   ├── service.py
│   │   │   ├── models.py
│   │   │   └── ports.py
│   │   │
│   │   ├── vad/
│   │   │   ├── service.py
│   │   │   ├── endpointing.py
│   │   │   └── models.py
│   │   │
│   │   └── interruption/
│   │       ├── manager.py
│   │       ├── cancellation.py
│   │       └── generation.py
│   │
│   ├── agent/
│   │   ├── graph.py
│   │   ├── state.py
│   │   ├── nodes/
│   │   │   ├── load_context.py
│   │   │   ├── reason.py
│   │   │   ├── execute_tool.py
│   │   │   └── respond.py
│   │   │
│   │   ├── routing/
│   │   │   ├── intent.py
│   │   │   └── tool_router.py
│   │   │
│   │   ├── prompts/
│   │   │   ├── system.py
│   │   │   └── personas.py
│   │   │
│   │   └── persona/
│   │       ├── config.py
│   │       └── service.py
│   │
│   ├── tools/
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── routing.py
│   │   │
│   │   ├── system/
│   │   │   └── current_time.py
│   │   │
│   │   ├── memory/
│   │   │   ├── save_memory.py
│   │   │   └── search_memory.py
│   │   │
│   │   ├── calendar/
│   │   │   ├── tools.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   │
│   │   └── email/
│   │       ├── tools.py
│   │       ├── schemas.py
│   │       └── service.py
│   │
│   ├── memory/
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── retrieval.py
│   │   ├── summarization.py
│   │   ├── policies.py
│   │   └── models.py
│   │
│   ├── conversations/
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   └── schemas.py
│   │
│   ├── users/
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   └── schemas.py
│   │
│   ├── integrations/
│   │   ├── deepgram/
│   │   │   ├── client.py
│   │   │   ├── stt.py
│   │   │   └── tts.py
│   │   │
│   │   ├── composio/
│   │   │   ├── client.py
│   │   │   ├── auth.py
│   │   │   ├── discovery.py
│   │   │   ├── calendar.py
│   │   │   └── gmail.py
│   │   │
│   │   ├── supabase/
│   │   │   ├── client.py
│   │   │   ├── conversations.py
│   │   │   ├── memory.py
│   │   │   └── users.py
│   │   │
│   │   └── llm/
│   │       ├── client.py
│   │       ├── models.py
│   │       └── provider.py
│   │
│   ├── observability/
│   │   ├── metrics.py
│   │   ├── tracing.py
│   │   ├── latency.py
│   │   └── events.py
│   │
│   └── shared/
│       ├── types.py
│       ├── constants.py
│       └── utils.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── e2e/
│
├── migrations/
├── scripts/
├── docs/
├── .env.example
├── pyproject.toml
├── docker-compose.yml
└── README.md
```

---

## 8. `core/`

`core` should contain application-wide infrastructure only.

Recommended contents:

```text
core/
├── config.py
├── dependencies.py
├── exceptions.py
└── logging.py
```

Responsibilities:

- application configuration;
- environment parsing;
- dependency injection/bootstrap;
- shared exception types;
- root logging configuration.

Do not turn `core` into a dumping ground.

If something clearly belongs to a feature, keep it inside that feature.

---

## 9. `realtime/`

The `realtime` feature owns persistent voice-session transport.

```text
realtime/
├── router.py
├── websocket.py
├── protocol.py
├── session.py
├── state.py
└── events.py
```

Responsibilities:

- accept WebSocket connections;
- authenticate sessions;
- receive audio frames;
- send server events;
- track connection state;
- coordinate session lifecycle;
- dispatch final transcripts to the agent;
- send TTS audio to the client;
- handle disconnect/reconnect;
- handle cancellation;
- clean up resources.

---

## 10. Typed WebSocket Protocol

Do not send arbitrary untyped JSON payloads everywhere.

Use explicit event contracts.

Example client events:

```text
client.session.start
client.audio
client.interrupt
client.cancel
client.session.end
```

Example server events:

```text
server.session.ready
server.transcript.interim
server.transcript.final
server.agent.thinking
server.tool.started
server.tool.completed
server.tts.audio
server.response.completed
server.interrupted
server.error
```

Typed event contracts make:

- frontend/backend evolution safer;
- debugging easier;
- tests deterministic;
- observability more useful.

---

## 11. `voice/`

The `voice` capability owns all speech-specific behavior.

Recommended subfeatures:

```text
voice/
├── stt/
├── tts/
├── vad/
└── interruption/
```

This keeps voice logic independent from LangGraph and tool logic.

---

## 12. STT Architecture

The internal STT interface should not depend directly on Deepgram.

Example protocol:

```python
from typing import Protocol, AsyncIterator

class SpeechToText(Protocol):
    async def stream(
        self,
        audio_stream: AsyncIterator[bytes],
    ) -> AsyncIterator["TranscriptEvent"]:
        ...
```

Domain/service code depends on `SpeechToText`.

Implementation:

```text
SpeechToText
    └── DeepgramSTT
```

Deepgram-specific SDK behavior stays under:

```text
integrations/deepgram/stt.py
```

---

## 13. TTS Architecture

Similarly:

```python
class TextToSpeech(Protocol):
    async def synthesize(
        self,
        text_stream,
    ):
        ...
```

Implementation:

```text
TextToSpeech
    └── DeepgramTTS
```

The rest of the system should not care whether TTS comes from Deepgram or another provider.

---

## 14. VAD and Endpointing

VAD and endpointing should remain conceptually separate from transcription.

They determine:

- speech start;
- speech continuation;
- user pause;
- endpoint detection;
- barge-in trigger.

Conceptual flow:

```text
LISTENING
   ↓ speech detected
USER_SPEAKING
   ↓ endpoint detected
FINAL_TRANSCRIPT
   ↓
AGENT_PROCESSING
```

Endpointing must be tunable.

Too aggressive:

```text
user pauses briefly
↓
agent incorrectly assumes turn is over
```

Too conservative:

```text
user finishes
↓
agent waits too long
↓
conversation feels slow
```

---

## 15. Interruption / Barge-In Module

Barge-in deserves its own module.

```text
voice/interruption/
├── manager.py
├── cancellation.py
└── generation.py
```

Responsibilities:

- detect interruption while agent is speaking;
- stop client playback;
- cancel/invalidate server-side TTS;
- invalidate old generation events;
- transition session state;
- preserve relevant context.

---

## 16. Generation IDs

Every agent response should have a unique generation ID.

Example:

```text
generation_id = 105
```

If generation `105` is interrupted:

```text
105 → stale
106 → active
```

Any later TTS packet from `105` is ignored.

This prevents stale audio from resuming after a user interruption.

---

## 17. `agent/`

The `agent` feature owns reasoning and orchestration.

It should not directly own:

- Deepgram logic;
- Composio SDK calls;
- Supabase queries;
- raw Gmail APIs.

Recommended structure:

```text
agent/
├── graph.py
├── state.py
├── nodes/
├── routing/
├── prompts/
└── persona/
```

---

## 18. LangGraph Design

Keep the first graph deliberately small.

Conceptual graph:

```text
START
  ↓
load_context
  ↓
agent
  ↓
Does agent need a tool?
  ├── No ─────────→ respond
  │
  └── Yes
       ↓
    tool_router
       ↓
    execute_tool
       ↓
      agent
       ↓
     respond
       ↓
      END
```

Do not create a large graph just because LangGraph supports one.

Complexity should be requirement-driven.

---

## 19. Agent State

Possible graph state:

```python
session_id
user_id
messages
current_transcript
available_tools
selected_tool
tool_results
memory_context
persona
response
generation_id
```

The graph state should hold application state.

Do not put long-lived network clients directly into serialized graph state.

---

## 20. Keep Infrastructure Out of LangGraph Nodes

Bad:

```python
async def calendar_node(state):
    composio = Composio(...)
    result = await composio.execute(...)
    supabase.table("messages").insert(...)
    return ...
```

Better:

```python
async def calendar_node(
    state: AgentState,
    calendar_service: CalendarService,
):
    result = await calendar_service.get_today_events(
        user_id=state.user_id
    )

    return {
        "tool_result": result
    }
```

Dependency chain:

```text
LangGraph node
    ↓
CalendarService
    ↓
CalendarGateway
    ↓
ComposioCalendarGateway
```

This keeps providers replaceable and testable.

---

## 21. `tools/`

Tools should be feature-oriented.

Recommended:

```text
tools/
├── base.py
├── registry.py
├── routing.py
├── system/
├── memory/
├── calendar/
└── email/
```

Avoid:

```text
tools/
├── tool1.py
├── tool2.py
├── tool3.py
├── tool4.py
```

Feature grouping becomes more important as the tool catalog grows.

---

## 22. MVP Tool Registry

Initial tool groups:

```python
TOOL_GROUPS = {
    "calendar": [
        get_today_events,
        check_calendar_availability,
    ],
    "email": [
        search_recent_email,
    ],
    "memory": [
        save_memory,
        search_memory,
    ],
    "system": [
        get_current_time,
    ],
}
```

Initial capabilities:

```text
get_current_time
save_memory
search_memory
get_today_events
check_calendar_availability
search_recent_email
```

---

## 23. Tool Registration Contract

Each tool should expose explicit metadata.

Conceptually:

```python
class ToolDefinition:
    name: str
    description: str
    capability: str
    read_only: bool
    requires_confirmation: bool
    timeout_seconds: float
    input_schema: type
```

This supports:

- discovery;
- permission checks;
- confirmation policy;
- timeout handling;
- UI descriptions;
- observability.

---

## 24. Tool Discovery Strategy

Do not rediscover the full Composio catalog on every turn.

Preferred flow:

```text
SESSION START
     ↓
Load user integrations
     ↓
Determine available capabilities
     ↓
Build tool registry
     ↓
Cache tool registry
```

Turn-time flow:

```text
User request
     ↓
Capability routing
     ↓
Small relevant tool subset
     ↓
LLM tool selection
     ↓
Execution
```

For six to ten tools, routing can remain simple.

Do not prematurely build a complicated hierarchy.

---

## 25. Hierarchical Tool Routing Later

When the catalog becomes large:

```text
                    User request
                         ↓
                  Capability Router
                         ↓
       ┌──────────┬──────┴──────┬─────────┐
       ▼          ▼             ▼         ▼
     EMAIL     CALENDAR       MEMORY     GENERAL
       ↓          ↓             ↓
  3 tools      4 tools        2 tools
```

Benefits:

- lower token overhead;
- less tool confusion;
- smaller schema volume;
- better tool selection.

---

## 26. Composio Boundary

Composio belongs in:

```text
integrations/composio/
```

Not scattered across tool files.

Example:

```text
integrations/composio/
├── client.py
├── auth.py
├── discovery.py
├── calendar.py
└── gmail.py
```

The tools layer knows application-level operations.

The Composio adapter translates them into provider calls.

---

## 27. Calendar Architecture

As Calendar grows, promote it from “just a tool” into a real feature.

Initial:

```text
tools/calendar/
├── tools.py
├── schemas.py
└── service.py
```

Later:

```text
features/calendar/
├── service.py
├── tools.py
├── models.py
├── permissions.py
├── prompts.py
└── repository.py
```

Promote it only when calendar behavior becomes meaningful beyond a couple of direct API operations.

---

## 28. Email Architecture

Initial:

```text
tools/email/
├── tools.py
├── schemas.py
└── service.py
```

The service may eventually own:

- query normalization;
- sender filtering;
- permission checks;
- result summarization;
- thread handling;
- attachment policies.

Composio remains the transport/integration implementation.

---

## 29. Read vs Write Tool Policy

Initial Composio tools should be read-only.

Examples:

```text
search email       → read
list calendar      → read
check availability → read
```

Future write actions:

```text
send email         → write
create event       → write
delete email       → destructive
cancel event       → destructive
```

Write/destructive tools require stronger policy enforcement.

---

## 30. Confirmation Architecture

Each tool should declare whether confirmation is required.

Conceptually:

```python
requires_confirmation = True
```

Flow:

```text
Agent proposes action
      ↓
Policy checks tool metadata
      ↓
Confirmation required?
   ├── No → execute
   └── Yes
         ↓
      ask user
         ↓
      user confirms
         ↓
      execute
```

Never report success until the tool result confirms success.

---

## 31. `memory/`

Memory should remain independent from conversation history.

Recommended:

```text
memory/
├── service.py
├── repository.py
├── retrieval.py
├── summarization.py
├── policies.py
└── models.py
```

Responsibilities:

- write selected long-term memory;
- retrieve relevant memories;
- summarize long sessions;
- enforce memory-writing policy;
- prevent indiscriminate storage.

---

## 32. Conversation History vs Long-Term Memory

Conversation history:

```text
what was said in this session
```

Long-term memory:

```text
selected information useful in future sessions
```

Do not conflate them.

Agent context should eventually be composed from:

```text
recent messages
+
conversation summary
+
retrieved relevant memories
+
current tool/session state
```

Do not send the user's complete lifetime history into every LLM call.

---

## 33. `conversations/`

This module owns persistent conversation records.

```text
conversations/
├── service.py
├── repository.py
├── models.py
└── schemas.py
```

Responsibilities:

- create sessions;
- save messages;
- load recent turns;
- close sessions;
- retrieve conversation history.

---

## 34. `users/`

This module owns application-level user state.

Possible responsibilities:

- application user ID;
- profile preferences;
- selected persona;
- integration metadata references;
- account state.

Authentication-provider specifics should remain outside the user domain.

---

## 35. Supabase Architecture

Supabase should remain an adapter.

Example:

```text
MemoryService
     ↓
MemoryRepository
     ↓
SupabaseMemoryRepository
```

Possible protocols:

```python
class MemoryRepository(Protocol):
    async def save(...): ...
    async def search(...): ...

class ConversationRepository(Protocol):
    async def create_session(...): ...
    async def append_message(...): ...
    async def recent_messages(...): ...
```

Concrete implementations:

```text
SupabaseMemoryRepository
SupabaseConversationRepository
```

---

## 36. Suggested Database Tables

Initial schema:

```text
users
sessions
messages
memories
tool_executions
connected_accounts
```

Example:

```text
sessions
--------
id
user_id
created_at
ended_at

messages
--------
id
session_id
role
content
created_at

memories
--------
id
user_id
content
embedding
importance
created_at
```

Tool execution table:

```text
tool_executions
---------------
id
session_id
user_id
tool_name
arguments
status
latency_ms
result_summary
created_at
```

---

## 37. Dependency Injection

Create long-lived clients during application startup where appropriate.

Examples:

```text
Deepgram client
Composio client
Supabase client
LLM client
```

Inject services/adapters rather than constructing SDK clients inside business logic.

Conceptually:

```text
FastAPI startup
    ↓
build dependencies
    ↓
services
    ↓
adapters
```

Benefits:

- testability;
- connection reuse;
- configuration;
- lifecycle management.

---

## 38. `integrations/`

All vendor-specific behavior should live here.

```text
integrations/
├── deepgram/
├── composio/
├── supabase/
└── llm/
```

The application layer should not care about SDK specifics.

---

## 39. Deepgram Adapter

```text
integrations/deepgram/
├── client.py
├── stt.py
└── tts.py
```

Responsibilities:

- SDK configuration;
- authentication;
- connection creation;
- streaming protocol conversion;
- provider-specific errors;
- retry behavior where appropriate.

Translate provider events into application-level events.

---

## 40. LLM Adapter

```text
integrations/llm/
├── client.py
├── models.py
└── provider.py
```

The agent should depend on an internal model interface where practical.

This makes model replacement and testing easier.

---

## 41. Avoid Excessive Interfaces

Use abstractions mainly at external or replaceable boundaries.

Good candidates:

```text
SpeechToText
TextToSpeech
CalendarGateway
EmailGateway
MemoryRepository
ConversationRepository
LLMProvider
```

Do not create protocols for every internal helper.

Excessive abstraction creates ceremony without real decoupling.

---

## 42. Real-Time Session State

Session state should explicitly represent the conversational lifecycle.

Possible states:

```text
LISTENING
USER_SPEAKING
ENDPOINT_DETECTED
THINKING
TOOL_EXECUTION
SPEAKING
INTERRUPTED
CLOSED
ERROR
```

Avoid arbitrary combinations of booleans such as:

```text
is_listening
is_speaking
is_processing
```

Prefer an explicit state machine.

---

## 43. Session Object

A session manager may track:

```python
session_id
user_id
connection
state
active_generation_id
active_tool_call
active_tts_task
last_final_transcript
created_at
last_activity_at
```

The session object coordinates infrastructure.

It should not become a business-logic god object.

---

## 44. Streaming Architecture

Desired hot path:

```text
microphone
   ↓
WebSocket
   ↓
Deepgram STT
   ↓
final transcript
   ↓
LangGraph
   ↓
LLM token stream
   ↓
sentence/phrase buffer
   ↓
Deepgram TTS
   ↓
WebSocket
   ↓
speaker
```

Avoid fully serial processing.

---

## 45. TTS Sentence/Phrase Buffer

Do not send every LLM token directly to TTS.

Use a buffer.

```text
LLM tokens
    ↓
text buffer
    ↓
phrase/sentence boundary
    ↓
TTS
```

This balances:

- latency;
- prosody;
- API call volume.

---

## 46. Tool Calls and the Voice Hot Path

External tool calls should not contaminate the audio transport design.

```text
audio pipeline
     ↓
agent
     ↓
tool layer
     ↓
external API
```

Composio is not part of STT/TTS.

This matters for maintainability and latency isolation.

---

## 47. Latency Budget and Instrumentation

Useful timestamps:

```text
audio_received_at
speech_started_at
speech_ended_at
final_transcript_at
agent_started_at
llm_first_token_at
tool_started_at
tool_finished_at
tts_requested_at
tts_first_audio_at
playback_started_at
response_completed_at
```

Track:

- endpoint latency;
- STT finalization latency;
- LLM time-to-first-token;
- tool latency;
- TTS time-to-first-audio;
- end-to-end time-to-first-audio;
- response completion latency;
- interruption cancellation latency.

---

## 48. Observability Architecture

Recommended:

```text
observability/
├── metrics.py
├── tracing.py
├── latency.py
└── events.py
```

Every turn should carry correlation identifiers:

```text
session_id
turn_id
generation_id
tool_execution_id
```

This is essential for debugging asynchronous real-time flows.

---

## 49. Error Handling

Classify errors explicitly.

Examples:

```text
STTConnectionError
TTSSynthesisError
ToolTimeoutError
ToolPermissionError
ToolExecutionError
MemoryRepositoryError
ConversationRepositoryError
AgentExecutionError
```

Vendor-specific exceptions should be translated at integration boundaries.

Do not leak raw SDK exceptions through the entire application.

---

## 50. Timeouts

Tool metadata should define timeout expectations.

Example:

```python
timeout_seconds = 5
```

Slow external APIs should fail gracefully.

The voice UX should not hang indefinitely waiting for a tool.

---

## 51. Retries

Retry only operations that are safe to retry.

Read operations are usually easier.

Write operations require idempotency.

Do not blindly retry:

```text
send_email
create_event
```

without safeguards.

---

## 52. Persona Architecture

Keep voice, tone, and persona separate.

```text
voice
    = acoustic identity

tone
    = response phrasing style

persona
    = persistent behavioral policy
```

Possible persona config:

```text
persona
├── identity
├── verbosity
├── warmth
├── assertiveness
├── humor
├── technical_depth
├── acknowledgement_style
├── interruption_behavior
└── action_confirmation_policy
```

---

## 53. Persona Service

Possible location:

```text
agent/persona/
├── config.py
└── service.py
```

Responsibilities:

- load selected persona;
- combine persona with system policy;
- expose structured configuration;
- avoid one giant unstructured prompt.

---

## 54. Suggested Personas

| Persona | Behaviour |
|---|---|
| Direct Warm Advisor | concise, confident, approachable |
| Technical Copilot | precise, technical, implementation-focused |
| Calm Executive Assistant | organized, restrained, anticipatory |
| Friendly Companion | conversational, curious, informal |
| Mentor | explanatory, challenging, educational |
| Minimalist Operator | very concise and action-oriented |
| Energetic Builder | proactive, fast-moving ideation |
| Safety-First Assistant | conservative around consequential actions |

---

## 55. Testing Strategy

Use four test levels:

```text
tests/
├── unit/
├── integration/
├── contract/
└── e2e/
```

---

## 56. Unit Tests

Unit test pure business logic.

Examples:

- tool routing;
- confirmation policy;
- persona config;
- memory selection;
- endpoint decision helpers;
- state transitions;
- generation invalidation.

Use fake adapters.

---

## 57. Integration Tests

Test adapters with real or sandbox providers when appropriate.

Examples:

- Deepgram STT adapter;
- Deepgram TTS adapter;
- Supabase repositories;
- Composio Calendar adapter;
- Composio Gmail adapter.

---

## 58. Contract Tests

Verify internal adapter contracts remain stable.

Examples:

```text
CalendarGateway
EmailGateway
SpeechToText
TextToSpeech
MemoryRepository
```

Useful when vendor adapters evolve.

---

## 59. End-to-End Tests

The most important E2E case:

```text
voice
→ STT
→ agent
→ tool
→ agent
→ TTS
→ interruption
→ new turn
```

This validates the actual product experience.

---

## 60. MVP Acceptance Scenario

User:

> "What's on my calendar today?"

System:

1. microphone is already active;
2. audio streams over WebSocket;
3. VAD detects speech;
4. Deepgram produces interim transcripts;
5. endpointing detects turn completion;
6. final transcript enters LangGraph;
7. agent determines Calendar tool is needed;
8. tool registry provides `get_today_events`;
9. Composio executes Calendar lookup.

Agent:

> "Checking."

Then:

> "You have three meetings. The first is at ten—"

User interrupts:

> "Just tell me the afternoon ones."

System must:

1. detect new user speech;
2. stop current TTS playback immediately;
3. invalidate the current generation;
4. transition to `USER_SPEAKING`;
5. continue STT;
6. finalize the interruption;
7. preserve calendar result/context;
8. understand that "ones" refers to today's meetings;
9. answer only the afternoon events.

Agent:

> "Two. One at two and another at four-thirty."

If this feels natural, the architecture is doing its job.

---

## 61. Recommended Build Sequence

### Phase 1 — Text Agent

```text
FastAPI
  ↓
LangGraph
  ↓
LLM
  ↓
text response
```

### Phase 2 — Streaming STT

```text
microphone
  ↓
WebSocket
  ↓
FastAPI
  ↓
Deepgram
  ↓
transcript
```

### Phase 3 — Streaming TTS

```text
agent response
  ↓
Deepgram TTS
  ↓
WebSocket
  ↓
speaker
```

### Phase 4 — VAD / Endpointing

Remove push-to-talk.

### Phase 5 — Barge-In

Add:

- interruption detection;
- playback cancellation;
- TTS cancellation;
- generation IDs;
- stale packet suppression.

### Phase 6 — Session Management

Add:

- session lifecycle;
- reconnect handling;
- cleanup;
- explicit state machine.

### Phase 7 — Persistence

Add Supabase:

- sessions;
- messages;
- users;
- tool logs.

### Phase 8 — First Composio Tool

Start with:

```text
get_today_events
```

### Phase 9 — Tool Registry

Expand to:

```text
get_current_time
save_memory
search_memory
get_today_events
check_calendar_availability
search_recent_email
```

### Phase 10 — Long-Term Memory

Add:

- memory write policy;
- retrieval;
- summaries;
- relevance filtering.

### Phase 11 — Persona System

Add structured persona configuration.

### Phase 12 — Observability and Optimization

Measure the complete real-time latency chain.

---

## 62. Code Ownership Rule

Every piece of code should answer:

> Which business capability owns this behavior?

Examples:

```text
calendar logic      → calendar feature
email logic         → email feature
session transport   → realtime
speech processing   → voice
reasoning           → agent
memory              → memory
Supabase specifics  → integrations/supabase
Composio specifics  → integrations/composio
Deepgram specifics  → integrations/deepgram
```

If ownership is unclear, the code is probably in the wrong place.

---

## 63. Shared Code Rule

Use `shared/` sparingly.

Good candidates:

```text
generic types
small constants
truly cross-cutting utility primitives
```

Bad candidates:

```text
calendar helper
gmail helper
memory helper
agent helper
```

If a utility is feature-specific, keep it with the feature.

---

## 64. Service Layer Rule

A feature service should contain meaningful application behavior.

Example:

```text
CalendarService.get_today_events()
```

may handle:

- user authorization;
- timezone normalization;
- gateway call;
- filtering;
- domain-level result normalization.

Do not create empty services that merely forward calls.

---

## 65. Repository Rule

Repositories abstract persistence.

Use them where persistence is meaningful.

Examples:

```text
ConversationRepository
MemoryRepository
UserRepository
```

Do not force every feature to have a repository.

Calendar and Gmail primarily need gateways because they call external APIs.

---

## 66. Gateway Rule

Use gateways for external capability APIs.

Examples:

```text
CalendarGateway
EmailGateway
```

Implementations:

```text
ComposioCalendarGateway
ComposioEmailGateway
```

Future options:

```text
GoogleCalendarGateway
MicrosoftCalendarGateway
GmailGateway
OutlookEmailGateway
```

This prevents permanent coupling to Composio.

---

## 67. Future Provider Flexibility

Architecture should permit:

```text
CalendarService
    ↓
CalendarGateway
    ├── ComposioCalendarGateway
    ├── GoogleCalendarGateway
    └── MicrosoftCalendarGateway
```

Likewise:

```text
SpeechToText
    ├── DeepgramSTT
    └── FutureSTTProvider
```

The MVP only implements one provider, but boundaries remain clean.

---

## 68. What Not to Abstract Yet

Do not abstract:

- every helper function;
- every model;
- every LangGraph node;
- every configuration field;
- internal logic with no realistic alternate implementation.

Create abstractions where replacement, testing, or boundary enforcement provides real value.

---

## 69. API Surface

Keep external API routes limited.

Initial:

```text
GET  /health
GET  /ready
WS   /voice/{session_id}
```

Potential later routes:

```text
GET  /sessions
GET  /sessions/{id}
GET  /integrations
POST /integrations/connect
GET  /personas
PUT  /users/me/persona
```

Do not expose every internal service as an HTTP endpoint.

---

## 70. Deployment Architecture

For the MVP:

```text
Browser / App
      ↓
FastAPI modular monolith
      ├── Deepgram
      ├── LLM provider
      ├── Composio
      └── Supabase
```

One main application deployment is sufficient.

---

## 71. Scaling Strategy

Scale vertically or horizontally before decomposing into services.

Possible later needs:

- multiple FastAPI instances;
- sticky or distributed session state;
- Redis for ephemeral shared state;
- queue for non-real-time work;
- external telemetry backend.

Do not introduce these until measurements justify them.

---

## 72. Real-Time vs Background Work

The hot path should remain minimal.

Hot path:

```text
audio
STT
agent
tool if required
TTS
```

Move non-critical work out of the immediate response path where possible.

Potential background work:

- conversation summarization;
- long-term memory extraction;
- analytics aggregation;
- transcript enrichment.

Do not delay spoken responses for optional background processing.

---

## 73. Security Boundaries

External tool execution must be tied to:

```text
user_id
session_id
connected_account
allowed capability
tool policy
```

Do not allow the model to invent arbitrary tool names or bypass the registry.

The registry is the enforcement boundary.

---

## 74. Tool Permission Architecture

Tool execution flow should eventually be:

```text
agent requests tool
      ↓
registry lookup
      ↓
capability available?
      ↓
user connected?
      ↓
permission allowed?
      ↓
confirmation required?
      ↓
execute
```

The LLM does not own authorization.

Application code does.

---

## 75. Important Anti-Patterns

Avoid:

```text
God service
God session manager
God LangGraph state
God tool registry
SDK calls inside graph nodes
SQL inside agent nodes
generic utils dumping ground
full tool discovery every turn
microservices before product validation
global mutable session dictionaries without lifecycle rules
untyped WebSocket messages
```

---

## 76. Final Architectural Recommendation

Use:

```text
Feature-oriented modular monolith
        +
Ports and adapters at external boundaries
        +
Explicit real-time state machine
        +
Cached feature-oriented tool registry
        +
Provider-specific integration adapters
        +
Structured observability
```

In practical terms:

```text
Feature based                  [YES]
Modular                        [YES]
Single deployment              [YES]
Clear boundaries               [YES]
Replaceable vendors            [YES]
Ports/adapters                 [YES]
Typed events                   [YES]
Explicit state                 [YES]

Microservices                  [NO]
Huge services folder           [NO]
Vendor SDKs in graph           [NO]
Dynamic discovery every turn   [NO]
Over-abstraction               [NO]
```

---

## 77. Core Architectural Principle

The project should optimize for this:

> **Product capabilities own behavior. Infrastructure adapters own vendors. The agent orchestrates; it does not become the entire application.**

That principle should remain true as the system grows from:

```text
6 tools
```

to:

```text
60+ tools
```

and from:

```text
one voice persona
```

to:

```text
multiple personas, users, integrations, and workflows
```

without forcing a complete rewrite.

---

## 78. Summary Decision

The codebase should be a **feature-based modular monolith**, not a purely module/layer-based application.

The final working pattern is:

```text
Feature / domain
    owns behavior

Ports / interfaces
    define external capabilities

Integration adapters
    own vendor-specific SDK behavior

LangGraph
    orchestrates application flow

FastAPI
    exposes the runtime and real-time session boundary
```

This gives the MVP enough structure to remain maintainable without burdening the project with premature distributed-system complexity.
