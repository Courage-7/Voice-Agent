# Voice Agent Stabilization, Tooling, Companion UX & Complex-Task Architecture
## Master Engineering Handoff for Coding Agent

**Status:** Architecture and implementation guidance  
**Execution model:** Incremental phases; implement and verify one phase at a time  
**Primary objective:** Turn the current voice agent into a low-latency, interruption-safe, tool-reliable, companion-like agent while preserving Deepgram Voice Agent as the real-time conversational runtime and making LangGraph the complex-task execution engine.

---

# 0. Read This First

This document is the engineering direction for the current `voice-agent` codebase.

It is based on:

1. the completed read-only codebase audit;
2. a senior architecture review of that audit;
3. current Deepgram Voice Agent / Flux TTS documentation;
4. current Composio Sessions documentation.

## Critical execution rule

**Do not implement this document all at once.**

The document defines the complete target architecture so that individual fixes do not contradict the eventual design. Implementation must happen in the numbered phases below.

For every phase:

1. inspect the affected code first;
2. make only the scoped changes;
3. add or update tests;
4. run the relevant test suite;
5. perform a focused runtime verification where applicable;
6. report exact files changed and behavior observed;
7. stop and wait for review before starting the next phase.

Do not delete existing architecture, files, or functionality merely because this document describes a new target. If removal or deprecation becomes appropriate, identify it in the report first.

Do not expose API keys, tokens, credentials, OAuth secrets, Supabase secrets, or authorization headers in logs or reports.

---

# 1. Current Codebase Findings That Must Be Treated as Baseline Facts

The diagnostic audit established the following current behavior.

## 1.1 Real-time voice architecture

The live voice path currently runs approximately as:

```text
Browser microphone
    ↓
FastAPI WebSocket
    ↓
Deepgram Voice Agent API
    ├── Nova-2 STT / VAD
    ├── Groq Think provider
    ├── function selection
    └── Aura TTS
    ↓
FastAPI WebSocket
    ↓
Web Audio API playback
```

The live path does **not** currently invoke the LangGraph graph.

LangGraph exists in the codebase, but it is not the real-time orchestrator.

That is not automatically a defect. The revised architecture intentionally keeps the low-latency real-time conversational loop separate from complex task orchestration.

---

## 1.2 Greeting

The current greeting is not configured using Deepgram's native `agent.greeting`.

The backend waits for `SettingsApplied`, then sends:

```json
{
  "type": "InjectAgentMessage",
  "content": "Hello! I'm here and ready to help."
}
```

This adds an unnecessary reactive message round-trip before TTS begins.

Current startup also includes a preliminary session POST followed by the WebSocket connection.

The session POST optimization is **not** part of the first change. Measure before deleting network steps.

---

## 1.3 Audio overlap and interruption

The frontend correctly stops currently scheduled Web Audio nodes when `UserStartedSpeaking` is received.

However:

- agent PCM is raw binary;
- incoming PCM has no client-side turn identity;
- late PCM frames that were already in flight can arrive after local playback is stopped;
- the frontend currently accepts those late frames and schedules them again;
- typed `InjectUserMessage` does not perform the same interruption cleanup as spoken barge-in.

This can produce stale speech tails, response collisions, and apparent overlapping voices.

---

## 1.4 Tool schema ambiguity

The LLM currently receives approximately 15 tool definitions.

The number `15` is not itself the central problem.

The problem is **semantic duplication**.

The model sees specialized functions such as:

```text
search_emails
send_email
list_calendar_events
create_calendar_event
perplexity_ai_research
...
```

while also receiving a broad:

```text
execute_app_action
```

that can perform overlapping operations.

This creates competing tool-selection paths.

---

## 1.5 Provider defaults are unsafe for multi-provider capabilities

Current tool defaults include behavior equivalent to:

```text
email -> Gmail by default
calendar -> Google Calendar by default
```

This is incorrect for a user who has Outlook connected, or both Gmail and Outlook connected.

The conversational model should not be expected to infer the correct provider from a hidden application default.

Provider resolution belongs in the backend capability layer.

---

## 1.6 Connected-account context is missing from live voice

The voice session currently builds prompt context using a hard-coded/default user identity and does not resolve active Composio connections before constructing the voice runtime.

This weakens:

- account selection;
- Gmail vs Outlook disambiguation;
- calendar provider selection;
- memory;
- user preferences;
- voice preference;
- confirmation state;
- personalization.

---

## 1.7 Tool safety is inconsistent

A specialized write tool such as email send requires confirmation, but the broad dynamic action tool can bypass that safety policy.

This is an architectural defect.

**Write safety must be enforced at the execution boundary after the concrete action has been resolved.**

It must not depend only on whichever model-facing tool happened to be selected.

---

## 1.8 Current TTS

The application currently uses Aura, e.g.:

```text
aura-asteria-en
```

Flux TTS is not implemented.

Runtime voice switching through Deepgram `UpdateSpeak` is not implemented.

---

## 1.9 Personality is intentionally too restrictive

The current prompt contains constraints equivalent to:

- keep nearly every response to one or two sentences;
- use an executive-assistant persona;
- aggressively avoid filler;
- ask the user what they want to do after simple acknowledgements.

Those instructions directly explain much of the rigid or robotic interaction.

---

## 1.10 Memory exists but is not part of live voice

The codebase contains conversation and memory services, but live voice initializes with empty memory context.

The agent therefore has less continuity than the surrounding architecture suggests.

---

## 1.11 Observability is incomplete

Deepgram `LatencyReport` is not currently handled even though it provides:

- STT latency;
- LLM time-to-first-token signals;
- text/tool/thinking token latency;
- TTS latency;
- total end-to-end latency.

Existing latency/metrics classes are not sufficiently wired into the live WebSocket path.

---

# 2. Non-Negotiable Architecture Decision

## Deepgram owns the real-time conversational hot path

The target real-time architecture is:

```text
                         ┌──────────────────────────┐
                         │      Browser / Client    │
                         │ mic + playback + UI      │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │   FastAPI Voice Gateway  │
                         │ session + policy bridge  │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                 ┌────────────────────────────────────────┐
                 │       Deepgram Voice Agent API         │
                 │                                        │
                 │  Listen        Think         Speak     │
                 │  STT/VAD  ->   LLM/tools  -> Flux TTS │
                 └───────────────┬────────────────────────┘
                                 │
                      FunctionCallRequest
                                 │
                                 ▼
                 ┌────────────────────────────────────────┐
                 │        Application Tool Layer          │
                 │ semantic tools + safety + resolution   │
                 └───────────────┬────────────────────────┘
                                 │
                  ┌──────────────┴──────────────┐
                  ▼                             ▼
          Simple/Direct Action            Complex Task
                  │                             │
                  ▼                             ▼
          Composio Session                LangGraph Engine
                  │                             │
                  │                       multi-step plan
                  │                       state/checkpoints
                  │                       tools/retries
                  │                       aggregation
                  │                             │
                  └──────────────┬──────────────┘
                                 ▼
                         FunctionCallResponse
                                 │
                                 ▼
                         Deepgram responds
                                 │
                                 ▼
                         Flux TTS playback
```

---

# 3. LangGraph's Final Role: Complex-Task Execution Engine

This is now an explicit architecture decision.

**LangGraph must become the complex-task execution engine.**

It must **not** process every conversational turn.

Examples that should remain in the normal Deepgram path:

```text
"Hello."
"What time is it?"
"What's on my calendar tomorrow?"
"Read my latest email."
"Search Perplexity for this."
"Send Sarah an email saying I'll be late."
```

Examples that may justify LangGraph:

```text
"Look through this week's emails, identify meetings that haven't been scheduled,
compare my calendar, draft replies for each person, and propose a schedule."
```

```text
"Research these three companies, compare their products, save the findings in a
document, and email me the summary."
```

```text
"Find the unresolved requests in my email, check whether any corresponding
calendar events exist, group them by urgency, then create a plan for me."
```

## 3.1 Why

Routing every utterance through LangGraph would add unnecessary:

- graph invocation overhead;
- serialization/state overhead;
- additional cancellation semantics;
- additional history synchronization;
- additional tool-routing complexity;
- latency for simple conversational turns.

The complex-task engine should only activate when graph orchestration provides value.

---

## 3.2 Complex-task classification

Introduce a deliberate classification boundary.

Conceptually:

```text
User request
    ↓
Can this be completed with:
- a direct conversational answer, OR
- one/few straightforward tool calls with limited branching?
    │
    ├── YES -> normal Deepgram function/tool path
    │
    └── NO -> complex_task function -> LangGraph
```

Do not use naive keyword matching alone.

The routing policy should consider:

- number of dependent steps;
- whether one tool result determines the next action;
- multiple apps/providers;
- iteration over collections;
- branching;
- aggregation/synthesis;
- retries;
- partial progress;
- need for checkpoint/resume;
- long-running execution;
- multi-artifact output;
- more than one externally visible write operation.

---

## 3.3 Model-facing complex-task function

The Deepgram Think model should eventually receive a clearly described function such as:

```text
run_complex_task
```

Suggested semantic contract:

```json
{
  "name": "run_complex_task",
  "description": "Execute a multi-step task that requires planning, multiple dependent tool calls, cross-app coordination, iteration, aggregation, retries, or checkpointed execution. Do not use for simple single-action requests.",
  "parameters": {
    "type": "object",
    "properties": {
      "goal": {
        "type": "string"
      },
      "constraints": {
        "type": "array",
        "items": {"type": "string"}
      }
    },
    "required": ["goal"]
  }
}
```

Do not blindly use this exact schema if the existing base-tool contracts require a different representation. Preserve local codebase conventions.

---

## 3.4 LangGraph execution contract

LangGraph should receive a normalized task request, not raw audio.

Suggested state:

```python
ComplexTaskState:
    task_id
    user_id
    session_id
    goal
    constraints
    conversation_context
    connected_capabilities
    plan
    current_step
    completed_steps
    tool_results
    pending_confirmation
    errors
    final_result
    status
```

Suggested lifecycle:

```text
RECEIVED
  ↓
PLAN
  ↓
VALIDATE_CAPABILITIES
  ↓
EXECUTE_STEP
  ↓
EVALUATE_RESULT
  ├── next step -> EXECUTE_STEP
  ├── clarification -> NEEDS_INPUT
  ├── confirmation -> NEEDS_CONFIRMATION
  ├── recoverable error -> RETRY/REPLAN
  └── finished -> SYNTHESIZE
                        ↓
                     COMPLETE
```

The graph should support checkpointing so a complex operation can be resumed rather than restarted.

---

## 3.5 LangGraph must use the same tool policy boundary

LangGraph must not develop its own ungoverned Composio execution path.

Both direct voice tool calls and LangGraph should converge on the same backend:

```text
Tool/Capability Service
    ↓
provider/account resolution
    ↓
authorization
    ↓
read/write/destructive classification
    ↓
confirmation/idempotency policy
    ↓
Composio Session execution
```

This prevents safety differences between simple and complex execution.

---

## 3.6 Complex-task conversation UX

The voice agent should not block silently while a complex graph runs.

Desired behavior:

```text
User:
"Go through this week's mail, find meetings I haven't scheduled,
and propose times."

Voice agent:
"I can do that. I'll check the messages against your calendar and
put together the gaps."

    ↓

run_complex_task(...)
    ↓

LangGraph executes

    ↓

If a decision is needed:
"I found two requests that don't specify a day. Should I include
both in the proposed schedule?"

    ↓

resume graph

    ↓

Final:
"I found four meeting requests without calendar entries. I've
grouped them by urgency and I have a proposed schedule ready."
```

Do not make the agent narrate every internal graph node.

---

# 4. Tool Architecture Target

## 4.1 Expose capabilities, not vendor-specific implementation details

The voice model should generally see semantic capabilities such as:

```text
search_email
get_email
send_email
reply_to_email
create_email_draft

list_calendar_events
get_calendar_availability
create_calendar_event
update_calendar_event

research
search_web

search_files
read_document
read_spreadsheet

run_complex_task
```

The LLM should not have to choose between low-level provider operations such as:

```text
GMAIL_FETCH_EMAILS
OUTLOOK_GET_EMAILS
```

unless provider specificity is actually part of the user's intent.

---

## 4.2 Backend provider resolution

Example:

```text
search_email(query="invoice")
          ↓
Capability Resolver
          ↓
Which email providers are connected?
          │
          ├── Gmail only -> Gmail
          ├── Outlook only -> Outlook
          ├── both + user explicitly said "Gmail" -> Gmail
          ├── both + user explicitly said "Outlook" -> Outlook
          ├── both + current conversation established provider -> reuse it
          └── both + genuinely ambiguous -> ask one concise clarification
```

Never silently default to Gmail merely because Gmail is first in code.

Same rule for calendars.

---

## 4.3 Remove semantic competition

Do not expose both:

```text
send_email
```

and a broad unrestricted:

```text
execute_app_action
```

for the same operation.

Options:

1. deprecate `execute_app_action` for already-modeled capabilities;
2. keep it only as a fallback for unmapped/less-common connected apps;
3. place it behind a backend discovery service rather than making it compete with common tools.

The chosen implementation must make the model-facing function surface unambiguous.

---

# 5. Tool Safety Policy

Safety and confirmation belong at the execution boundary.

Suggested classification:

```text
READ
- search email
- read email
- list calendar
- read document
- search Drive
- research

WRITE
- send email
- reply to email
- create event
- update document
- append spreadsheet row

DESTRUCTIVE / HIGH IMPACT
- delete email
- delete event
- permanently modify/delete document
- revoke access
- other destructive account actions
```

Suggested execution:

```text
resolved concrete action
        ↓
classify
        ↓
READ --------------------------> execute
WRITE -------------------------> confirmation policy
DESTRUCTIVE/HIGH IMPACT -------> explicit confirmation
```

No generic/dynamic tool is allowed to bypass this.

## 5.1 Idempotency

Externally visible writes must be protected from accidental duplication.

Particularly:

- sending email;
- replying to email;
- creating calendar events;
- document creation;
- repeated updates after timeout/reconnect.

Design an idempotency strategy before retrying write operations automatically.

---

# 6. Composio Target Architecture

The current code uses direct execution.

The target is to evaluate and migrate the application tool layer toward **Composio Sessions**.

A Composio Session should scope:

- stable application user ID;
- allowed toolkits;
- connected accounts;
- authentication;
- tool discovery;
- execution context.

## 6.1 Important version check

The audit found dependencies around:

```text
composio-core >= 0.6.0
composio-langchain >= 0.6.0
```

Current Composio Sessions functionality has newer SDK requirements for some features such as preloaded tools.

Do not upgrade blindly.

During the Composio phase:

1. inspect the exact installed package versions;
2. inspect deprecated/current package naming;
3. review current Composio migration documentation;
4. produce an upgrade-impact assessment;
5. upgrade only when tests and compatibility changes are understood.

The presence of `composio-langchain` must also be reviewed. If the live architecture does not use it, do not keep it merely by habit, but do not remove it without confirming imports and tests.

---

## 6.2 Session toolkit scope

The session should not have uncontrolled access to every toolkit in Composio.

Build the enabled toolkit list from the application's supported/connected integrations.

Current project audit identified approximately:

```text
Gmail
Outlook
Google Calendar
Perplexity AI
SerpAPI
Google Sheets
Google Docs
Google Drive
```

Resolve the actual runtime list from the code and connected-account state.

---

## 6.3 Common tools vs runtime discovery

For common voice operations, prefer a small deterministic model-facing capability surface.

For less-common apps/actions, use dynamic discovery beneath the application tool layer.

Do not dump hundreds of Composio schemas into the Deepgram Think context.

---

# 7. Canonical User Identity

Remove reliance on:

```text
default_user
```

for real sessions.

The target identity chain is:

```text
Authenticated application user
            ↓
stable internal user_id
            ↓
      voice session
       /         \
      ↓           ↓
Supabase       Composio
profile         user_id
```

The same stable ID should scope:

- connected accounts;
- voice preference;
- persona;
- memory;
- conversations;
- confirmation state;
- complex tasks;
- LangGraph checkpoints.

Do not use email addresses as hidden stand-ins for user identity unless the application identity model explicitly defines that.

---

# 8. Flux TTS Target

The project currently uses Aura.

The target TTS should support Flux explicitly.

Current Deepgram Voice Agent configuration is conceptually:

```json
{
  "agent": {
    "speak": {
      "provider": {
        "type": "deepgram",
        "version": "v2",
        "model": "flux-alexis-en",
        "speed": 1.0
      }
    }
  }
}
```

Use a currently supported Flux voice from the official Deepgram catalog.

Do not hardcode a list from memory without a centralized catalog/config abstraction.

---

# 9. Voice Selection

Voice choice must become a first-class setting.

Support:

1. a persisted preferred voice;
2. a session-level temporary override.

Target:

```text
UserProfile.preferred_voice
           ↓
default for new voice sessions

UI voice selector
           ↓
session override
           ↓
UpdateSpeak
```

Current Deepgram Voice Agent `UpdateSpeak` uses the nested `speak.provider` structure.

Conceptual payload:

```json
{
  "type": "UpdateSpeak",
  "speak": {
    "provider": {
      "type": "deepgram",
      "version": "v2",
      "model": "flux-alexis-en"
    }
  }
}
```

The new Flux voice should apply on the next agent turn.

Handle the acknowledgement:

```text
SpeakUpdated
```

and report/update UI state only after a successful acknowledgement.

Handle error responses without corrupting the active session.

---

# 10. Voice Selector UX

The selector should eventually provide:

- human-readable voice name;
- model ID internally;
- optional description/accent metadata;
- preview/sample capability if practical;
- selected state;
- saved-as-default option;
- temporary session switching.

Do not expose arbitrary model text input to ordinary users.

Use an allowlisted catalog.

---

# 11. Greeting Architecture

The fixed greeting belongs in:

```text
agent.greeting
```

inside the initial Deepgram `Settings`.

It should not require:

```text
SettingsApplied
    ↓
InjectAgentMessage
```

before synthesis begins.

Keep the greeting short.

Do not use the LLM to create a fixed startup greeting.

Later, if the product needs a personalized greeting, evaluate the latency tradeoff deliberately instead of quietly reintroducing an LLM dependency.

---

# 12. Interruption & Audio Playback Target

## 12.1 Spoken barge-in

Desired behavior:

```text
Agent speaking
    ↓
UserStartedSpeaking
    ↓
stop local audio immediately
    ↓
enter suppression state
    ↓
discard old/in-flight agent PCM
    ↓
Deepgram processes new user turn
    ↓
next AgentStartedSpeaking
    ↓
exit suppression state
    ↓
play new agent PCM
```

Do not invent a custom binary envelope in the first fix.

Do not use the standalone Flux `/v2/speak` `Interrupt` protocol as though it were a Voice Agent client message.

The Voice Agent API's barge-in event is `UserStartedSpeaking`, and local playback must stop immediately.

---

## 12.2 Typed interruption

Typing a new request while the agent is speaking should behave like a user interruption.

Before sending `InjectUserMessage`:

```text
if agent audio is active:
    stop playback
    enable suppression
send InjectUserMessage
wait for next AgentStartedSpeaking
resume new response audio
```

The same state machine should protect both voice and text input.

---

## 12.3 Playback state

Introduce explicit client playback state instead of relying only on `activeAudioSources`.

Suggested conceptual state:

```text
playbackSuppressed: bool
agentSpeaking: bool
lastInterruptionAt
```

A generation/turn ID may still be useful later, but do not mutate the PCM transport before proving the simpler suppression boundary is insufficient.

---

# 13. Deepgram Think Configuration Investigation

The audit identified a hard-coded:

```text
provider.type = groq
model = openai/gpt-oss-20b
```

and no visible Think endpoint.

Current Deepgram documentation states that a Groq Think provider requires an endpoint configuration.

Do not change the model during the first phase.

Capture the actual outgoing runtime Settings payload with secrets redacted.

Determine:

- exact provider type;
- exact model;
- whether `endpoint` exists at runtime;
- whether headers/credentials are injected elsewhere;
- whether Deepgram emits Warning or Error;
- whether Deepgram is falling back to any managed provider/model.

Also reconcile later:

```text
openai/gpt-oss-20b
groq/compound
README model references
```

Do not choose based on naming alone.

---

# 14. Companion Experience Target

The agent should feel like a capable conversational companion, not a command-line interface with speech.

This does **not** mean:

- pretending to be human;
- excessive emotional language;
- constant jokes;
- filler before every action;
- unnecessarily long responses;
- manufactured personality that interferes with task reliability.

It means:

- continuity;
- natural acknowledgements;
- varied but grounded wording;
- remembering the current conversational thread;
- handling corrections as corrections;
- natural tool transitions;
- flexible spoken response length;
- useful initiative when appropriate;
- fewer robotic reset questions.

---

# 15. Proposed Voice Agent Prompt

**Do not apply this prompt during Phase 1.**

This is the target prompt direction for the companion/personality phase.

Preserve any critical existing safety/tool-contract instructions that are not represented below.

```text
You are a capable conversational voice companion with access to the user's
connected tools and services.

PRIMARY BEHAVIOR

Speak naturally and conversationally. Be concise when the answer is simple,
but do not force every reply into the same one- or two-sentence structure.
Let response length follow the situation and the user's level of detail.

Maintain continuity across turns. Treat corrections, follow-up questions,
references such as "that one", "instead", "the second one", and short
acknowledgements as part of the current conversation unless there is clear
evidence that the user has changed topics.

Do not repeatedly reset the conversation with phrases like "How can I help?"
after the user says "okay", "yeah", "sure", "cool", "right", or similar
acknowledgements. Respond only when a response is useful.

VOICE DELIVERY

Responses will be spoken aloud.

Use plain, natural spoken language.
Avoid markdown, tables, code formatting, raw JSON, internal tool names,
database identifiers, action slugs, or implementation details unless the user
explicitly asks for technical details.

Do not sound like a status console.

Prefer:
"Let me check your calendar."

Avoid:
"Executing GOOGLECALENDAR_FIND_EVENT."

Prefer:
"I found two meetings tomorrow morning."

Avoid:
"The tool returned 2 results."

CONVERSATIONAL STYLE

Be attentive, calm, natural, and engaged.

Vary acknowledgements based on context rather than using one canned phrase.

Do not add filler merely to sound friendly.
Do not overuse the user's name.
Do not pretend to have emotions, a body, or human experiences.

When the user interrupts or corrects a request, adapt to the latest instruction.
Do not continue defending or completing the obsolete interpretation unless an
external action may already have been committed.

TOOLS

Use tools only when external information or an external action is required.

Choose the semantic capability that directly matches the user's intent.

Do not choose a provider merely because it is a default.
If the user explicitly names Gmail, Outlook, Google Calendar, or another
service, respect that provider.

When the user does not name a provider, rely on the application's connected
account resolution. If the backend indicates genuine ambiguity between multiple
valid providers and the conversation has not established one, ask one short
clarifying question.

Do not expose Composio action slugs or internal provider-routing details.

Use tool results as evidence. Do not claim an email was sent, an event was
created, or a file was changed until execution reports success.

READS AND WRITES

Read-only operations may normally proceed without confirmation.

For externally visible writes, follow the application's confirmation policy.
Never bypass confirmation using a generic or dynamic action route.

If a write fails or times out, do not blindly retry if doing so could create a
duplicate external action.

MULTI-STEP REQUESTS

Handle simple requests directly.

If the request requires substantial multi-step planning, dependent actions
across several tools, iteration, aggregation, checkpointing, or complex
cross-application coordination, use the complex-task execution capability.

Do not use the complex-task engine for ordinary conversation or a simple
single-tool request.

TOOL WAITING

Do not narrate every internal step.

For a tool that may take noticeable time, a short contextual acknowledgement
is acceptable, for example:

"Let me check that."
"I'll look through those messages."
"I'll compare that with your calendar."

Do not begin multiple spoken responses that can overlap.

MEMORY AND CONTEXT

Use relevant conversation context and saved preferences when provided.

Do not repeat a question the user has already answered in the current context.

Use prior tool results when they remain valid and relevant, but refresh
time-sensitive external information when needed.

If an assistant response was interrupted, do not assume the user heard the
entire response when the runtime provides more accurate interruption state.

ERRORS

Translate technical failures into concise user-facing explanations.

Do not read stack traces, HTTP status payloads, OAuth internals, or raw
exceptions aloud.

If authentication is required, tell the user which service needs to be
connected or reconnected.

If an operation cannot safely continue without clarification, ask only for the
missing information.

GOAL

The experience should feel like an ongoing conversation with a capable,
reliable companion that can act through connected services — not a sequence of
isolated commands sent to a tool runner.
```

---

# 16. Tool-Use Prompt Guidance

When the tool layer is redesigned, add explicit instructions equivalent to:

```text
For email requests:
- respect an explicitly named provider;
- otherwise use backend provider resolution;
- do not default to Gmail in the language model;
- distinguish search/read, draft, send, and reply;
- a reply must target the actual message/thread context when required.

For calendar requests:
- respect an explicitly named provider;
- otherwise use backend provider resolution;
- resolve time ranges carefully;
- do not create an event when the user only asked to inspect availability.

For research:
- use Perplexity/research when synthesis or current external research is
  explicitly needed;
- do not invoke research for ordinary conversation.

For complex tasks:
- use run_complex_task only when the request genuinely requires orchestration,
  dependent steps, cross-app work, iteration, aggregation, or checkpointing.
```

Keep tool descriptions distinct and non-overlapping.

---

# 17. Memory Target

The live voice runtime should eventually receive relevant context from:

- current conversation;
- stable user preferences;
- preferred voice;
- relevant saved memories;
- recent tool state when appropriate;
- complex task/checkpoint state.

Do not indiscriminately inject all stored memories.

Use relevance and bounded context.

Deepgram Voice Agent supports conversation context/history; use the appropriate context mechanism rather than stuffing all history into the main system prompt.

---

# 18. Interrupted Response State

The audit indicates the backend can persist an assistant response as though it was fully spoken even when the user interrupted the audio.

This must eventually be reconciled.

For the Voice Agent API path, distinguish:

```text
generated assistant text
```

from:

```text
what the user was likely presented/heard
```

Do not falsely assume every generated response was fully delivered.

Do not implement the standalone Flux TTS `SpeechInterrupted` protocol unless the architecture actually uses the standalone `/v2/speak` socket. The Voice Agent integration and standalone Flux TTS integration have different client-message contracts.

---

# 19. Observability Target

Capture enough telemetry to answer:

```text
Where did this turn spend its time?
```

## Server-side

At minimum:

```text
session_started_at
deepgram_ws_connected_at
settings_sent_at
settings_applied_at

user_started_speaking_at
agent_thinking_at

function_call_received_at
tool_started_at
tool_completed_at

agent_started_speaking_at
agent_audio_done_at

LatencyReport:
    stt_latency
    ttt_token_latency
    ttt_text_latency
    ttt_tool_latency
    ttt_thinking_latency
    tts_latency
    total_latency

Warning
Error
SpeakUpdated
ThinkUpdated
```

Every optional `LatencyReport` field must be parsed defensively.

## Client-side

Measure where practical:

```text
microphone start
WebSocket open
first greeting audio received
first greeting audio scheduled
first greeting audio played

barge-in event received
playback stopped
suppression enabled
suppression released
```

Do not create excessively verbose production logs containing raw transcripts or sensitive tool data by default.

---

# 20. Testing Strategy

Add targeted tests incrementally.

## Voice configuration

- greeting is in initial Settings;
- greeting is not injected again after SettingsApplied;
- expected listen/think/speak configuration is serialized;
- Flux `v2` configuration when migration occurs;
- `UpdateSpeak` is correctly serialized;
- `SpeakUpdated` is handled.

## Audio interruption

- `UserStartedSpeaking` stops active playback;
- suppression activates;
- stale PCM while suppressed is dropped;
- next `AgentStartedSpeaking` releases suppression;
- typed interruption follows the same state;
- idle text injection does not unnecessarily corrupt playback state.

## Tool routing

- Gmail-only user;
- Outlook-only user;
- both connected with explicit Gmail request;
- both connected with explicit Outlook request;
- both connected with previously established provider context;
- both connected with unresolved ambiguity;
- no provider connected;
- disconnected/expired OAuth.

## Safety

- read operation proceeds correctly;
- send/reply requires correct policy;
- generic/dynamic routes cannot bypass write confirmation;
- retries do not duplicate a write.

## Multi-step

- direct simple tool request does not invoke LangGraph;
- complex request invokes `run_complex_task`;
- graph checkpoints;
- graph can pause for clarification;
- graph can pause for confirmation;
- graph resumes;
- graph partial failure does not incorrectly report total success.

## Memory/personality

- acknowledgement does not automatically trigger "How can I help?";
- follow-up references maintain context;
- provider preference can persist if deliberately modeled;
- saved voice preference is applied to new sessions.

---

# 21. PHASED IMPLEMENTATION PLAN

---

# PHASE 1 — Voice Hot-Path Stabilization & Measurement

## Goal

Fix the confirmed greeting/interruption defects and establish latency evidence before changing models, tool architecture, personality, or orchestration.

## Files likely involved

Audit identified:

```text
app/integrations/deepgram/agent_session.py
app/realtime/session.py
app/realtime/playground.html
app/observability/latency.py
app/observability/metrics.py
relevant tests
```

Confirm exact current symbols before editing.

---

## Phase 1.1 Native greeting

Move the existing fixed greeting into the initial Deepgram Settings:

```text
agent.greeting
```

Remove only the now-redundant:

```text
SettingsApplied -> InjectAgentMessage greeting
```

path.

Do not change the greeting wording yet.

Do not eliminate the preliminary REST session call yet.

Measure it first.

---

## Phase 1.2 Spoken barge-in suppression

Implement client-side suppression:

```text
normal
  ↓
UserStartedSpeaking
  ↓
stopAllAudioPlayback()
  ↓
playbackSuppressed = true
  ↓
drop incoming agent binary PCM
  ↓
next AgentStartedSpeaking
  ↓
playbackSuppressed = false
  ↓
play new PCM
```

Ensure the first new-turn PCM is not accidentally lost because of event ordering.

Inspect actual Deepgram event ordering in runtime logs.

Do not invent a custom PCM envelope in this phase.

---

## Phase 1.3 Typed interruption

When a user submits `InjectUserMessage` while the agent is speaking:

1. stop current local playback;
2. enable suppression;
3. send the user message;
4. release suppression at the next valid new response boundary.

When the agent is idle, normal typed input should still work without unnecessary state changes.

---

## Phase 1.4 LatencyReport

Handle:

```text
LatencyReport
```

Log/store optional fields safely.

Wire existing latency/metric abstractions only where doing so remains simple and consistent with their design.

Do not redesign observability infrastructure merely to complete this phase.

---

## Phase 1.5 Runtime Think inspection

Capture the exact outgoing `agent.think` configuration with secrets redacted.

Specifically report:

```text
provider.type
provider.model
endpoint presence
endpoint URL host/path if safe to report
headers PRESENT/ABSENT without values
temperature if present
```

Capture any Deepgram:

```text
SettingsApplied
Warning
Error
```

Do not change the Think model yet.

---

## Phase 1.6 Tests

Add focused tests for the changes.

Where browser-only behavior cannot be tested with the current test stack, isolate the state logic enough to test it or provide a deterministic manual test protocol.

---

## Phase 1 Acceptance Criteria

- greeting is configured natively;
- no duplicate late greeting injection;
- spoken interruption stops old speech;
- late old PCM does not re-enter playback before new-turn boundary;
- typed interruption stops old speech;
- agent resumes with new response;
- no new overlapping-audio regression observed in targeted testing;
- LatencyReport is captured;
- actual Groq Think configuration is documented;
- existing relevant tests pass.

---

## PHASE 1 REPORT REQUIRED

Return:

1. exact files changed;
2. symbols/functions changed;
3. concise diff summary per file;
4. tests added/changed;
5. complete test results;
6. before/after greeting lifecycle;
7. before/after interruption lifecycle;
8. sample redacted LatencyReport log/record;
9. actual redacted Think configuration;
10. Deepgram warnings/errors observed;
11. measured greeting timing before/after if possible;
12. measured turn timing sample if possible;
13. anything deliberately not changed.

**STOP AFTER PHASE 1.**

Do not start Phase 2 until this report is reviewed.

---

# PHASE 2 — User Identity, Tool Semantics, Provider Resolution & Safety

Do not implement before Phase 1 review.

## Goals

- remove `default_user` from actual live sessions;
- introduce canonical user identity;
- eliminate Gmail/Google hard-coded provider bias;
- remove specialized-vs-generic schema collision;
- centralize confirmation/safety;
- fix known entity/user propagation defects;
- preserve existing integrations.

## Required design before code

Produce a short design showing:

```text
Deepgram semantic function
    ↓
Capability Service
    ↓
Connected Account Resolver
    ↓
Concrete Provider/Action
    ↓
Safety Policy
    ↓
Execution
```

Document exact current tool registrations and show the proposed reduced/clean model-facing surface.

## Provider resolution acceptance cases

Must correctly handle:

```text
Gmail only
Outlook only
both, explicit Gmail
both, explicit Outlook
both, conversation already established provider
both, ambiguous
none connected
expired/disconnected account
```

## Safety acceptance cases

A broad/fallback capability must never bypass:

```text
send/reply/create/update/delete confirmation policy
```

## Known audit defect to verify/fix

Workspace tools were reported to omit the current user/entity identifier when calling Composio.

Verify and correct only if confirmed in current code.

---

# PHASE 3 — Composio Sessions Migration

Do not implement before Phase 2 review.

## Goal

Move from ad-hoc direct tool execution toward a user-scoped Composio Session architecture.

## First step: compatibility assessment

Before dependency changes, report:

- installed Composio versions;
- packages actually imported;
- current API usage;
- deprecated APIs;
- migration requirements;
- tests affected;
- whether `composio-langchain` is used anywhere.

Then propose exact package/version changes.

## Target

```text
application user
    ↓
Composio session
    ↓
enabled toolkits
    ↓
connected accounts
    ↓
tool discovery/execution
```

Keep common voice capabilities deterministic.

Use Composio dynamic discovery primarily for less-common/unmapped actions.

Do not indiscriminately expose all session meta tools to the voice LLM if it makes routing less predictable.

---

# PHASE 4 — Aura to Flux TTS + Voice Switching

Do not implement before prior phase review unless explicitly reprioritized.

## Goals

- migrate `speak.provider` to Flux TTS `v2`;
- preserve audio format compatibility;
- add allowlisted voice catalog;
- support preferred voice;
- support runtime `UpdateSpeak`;
- handle `SpeakUpdated`;
- add UI selector.

## Requirements

Initial Flux configuration must explicitly use:

```text
provider.type = deepgram
provider.version = v2
provider.model = flux-...-en
```

Do not rely on an implicit default when the application has a user-selectable voice feature.

## Voice preference

Support:

```text
persistent preferred voice
+
temporary per-session override
```

Do not force one or the other.

## Speed / expressivity

Do not optimize personality by aggressively increasing expressivity.

Start with production-safe/default delivery.

Evaluate speed/expressivity experimentally after correctness and voice selection work.

---

# PHASE 5 — Companion Prompt & Conversational Behavior

Do not implement before the voice/tool foundations are stable.

## Goals

- remove rigid universal 1–2 sentence rule;
- move from executive-assistant default to conversational companion;
- eliminate repetitive reset prompts;
- improve contextual acknowledgements;
- improve correction/follow-up behavior;
- hide tool implementation details;
- preserve accuracy and action safety.

Use the proposed prompt in Section 15 as the starting point.

Before replacement:

1. compare it against all current prompt requirements;
2. identify safety/tool instructions that must be preserved;
3. merge rather than accidentally deleting necessary constraints;
4. add prompt tests;
5. test with recorded conversational scenarios.

## Required conversational scenarios

```text
User: "Hi."
Agent: natural greeting, no unnecessary tool use.

User: "Check my calendar tomorrow."
Agent: natural acknowledgement/tool execution/result.

User: "Actually, only after ten."
Agent: treats as correction to current request.

User: "Okay."
Agent: does not automatically reset with "How can I help?"

User: "Use Outlook instead."
Agent: changes provider context naturally.

User interrupts mid-result:
Agent stops old speech and handles new direction.
```

---

# PHASE 6 — Memory & Context Integration

## Goals

Connect live voice to bounded relevant memory.

Include:

- user preferences;
- voice preference;
- relevant profile details;
- current conversational context;
- relevant prior tool results;
- relevant complex-task state.

Avoid loading all Supabase memory into every voice session.

Use relevance and context limits.

Investigate Deepgram `agent.context` for proper conversation/history injection rather than embedding conversation history inside the system prompt.

---

# PHASE 7 — LangGraph Complex-Task Engine

This phase is required.

LangGraph is not being deprecated.

LangGraph's role is being made explicit and useful.

## Goal

Implement:

```text
run_complex_task
```

as the boundary from the real-time voice agent into LangGraph.

## Requirements

LangGraph should:

- receive structured task goal/context;
- plan dependent steps;
- call the shared capability/tool execution layer;
- work across multiple connected apps;
- checkpoint state;
- pause for clarification;
- pause for confirmation;
- resume safely;
- handle partial failures;
- aggregate results;
- return a concise normalized final result to Deepgram.

## It must not

- handle every hello;
- own the microphone;
- own raw PCM playback;
- replace Deepgram turn detection;
- add itself to every simple function call;
- maintain a completely separate ungoverned tool stack.

## Complex-task examples to implement in tests

### Example A — Email/calendar coordination

```text
"Look through this week's emails, identify meeting requests that aren't on
my calendar, compare my availability, draft replies, and propose times."
```

Expected broad graph:

```text
search email
    ↓
extract candidate meeting requests
    ↓
list relevant calendar events / availability
    ↓
match requests to calendar
    ↓
propose times
    ↓
draft replies
    ↓
request confirmation before externally visible writes if needed
    ↓
return summary
```

### Example B — Research + document + email

```text
"Research these three companies, compare them, save the summary to a document,
and email me the link."
```

Expected graph:

```text
research each company
    ↓
normalize findings
    ↓
compare
    ↓
create document
    ↓
prepare email
    ↓
confirmation policy
    ↓
send
```

### Example C — Recoverable interruption

Graph is executing.

User changes one constraint.

The system should update/resume the complex task if safe rather than restarting everything blindly.

---

# PHASE 8 — Advanced Turn-Taking and Optimization

Only after correctness.

Evaluate:

- Deepgram Flux STT if appropriate;
- explicit endpointing/eot tuning;
- eager end-of-turn only after cancellation semantics are stable;
- acknowledgement timing during tool latency;
- playback buffering;
- model latency;
- prompt/token size;
- tool-result compaction;
- connection/startup optimizations.

Do not optimize by intuition.

Use the collected latency measurements.

---

# 22. Performance Principles

Priority order:

```text
1. correctness
2. interruption safety
3. tool/action correctness
4. write safety
5. observability
6. conversational quality
7. latency optimization
8. advanced speculative/eager execution
```

Do not trade tool correctness for a small latency reduction without measuring the impact.

Do not add premature concurrency around externally visible writes.

---

# 23. Tool Result Compaction

The audit found the generic action path may return large raw Composio payloads.

The application tool layer should normalize tool results before returning them to the voice LLM.

Examples:

Email search:

```json
{
  "items": [
    {
      "message_id": "...",
      "thread_id": "...",
      "sender": "...",
      "subject": "...",
      "received_at": "...",
      "preview": "..."
    }
  ]
}
```

Calendar:

```json
{
  "events": [
    {
      "event_id": "...",
      "title": "...",
      "start": "...",
      "end": "...",
      "provider": "..."
    }
  ]
}
```

Preserve identifiers required for the next action.

Do not compact away IDs and then expect the agent to perform a valid reply/update step.

---

# 24. Multi-Step Email Requirement

The audit specifically noted that searching email and then replying may fail if the first tool result omits message/thread IDs.

Correct this in the tool architecture.

A request such as:

```text
"Reply to John's latest email and tell him I'll send the document tomorrow."
```

requires:

```text
search/read
    ↓
return message/thread identity
    ↓
resolve intended message
    ↓
construct reply
    ↓
confirmation policy
    ↓
reply action
```

Do not turn a reply into a brand-new email unless that is intentionally the fallback and the user approves it.

---

# 25. Connected App Awareness

At session startup or capability initialization, build a safe connected-capabilities representation such as:

```json
{
  "email": ["gmail", "outlook"],
  "calendar": ["googlecalendar", "outlook"],
  "research": ["perplexityai", "serpapi"],
  "workspace": ["googledrive", "googledocs", "googlesheets"]
}
```

This representation can drive backend resolution.

Do not inject raw OAuth/account records into the prompt.

---

# 26. Error UX

Translate infrastructure failures.

Bad:

```text
"ConnectedAccountNotFound: auth config 8d..."
```

Better:

```text
"Your Outlook connection isn't available right now. You'll need to reconnect
it before I can check that mailbox."
```

Bad:

```text
"Function execution returned 422."
```

Better:

```text
"I couldn't complete that because the event details are missing a start time."
```

Preserve full technical errors in server logs with appropriate redaction.

---

# 27. Confirmation UX

Confirmation should sound natural.

Example:

```text
"I found John's latest message. You want me to reply:
'I'll send the document tomorrow.' Should I send it?"
```

For a calendar event:

```text
"I can create that for Tuesday at 10 AM for 30 minutes. Want me to add it?"
```

Avoid:

```text
"Confirm execution of OUTLOOK_SEND_MAIL."
```

---

# 28. Agent Acknowledgement During Slow Tools

Do not make the user stare into silence for a long-running read operation if a short acknowledgement improves UX.

But do not allow acknowledgement audio to overlap with final response audio.

Possible policy:

```text
fast operation -> no acknowledgement; answer when ready

noticeably slow operation -> one short contextual acknowledgement

complex task -> acknowledge task start, then only speak again for:
    clarification
    confirmation
    meaningful checkpoint if appropriate
    final result
```

Instrument before setting hard thresholds.

---

# 29. Do Not Make These Changes Prematurely

Until their phases:

- do not delete LangGraph;
- do not put LangGraph into every voice turn;
- do not switch models simply because one is named in config;
- do not expose all Composio action schemas;
- do not add a custom PCM protocol;
- do not use standalone Flux TTS client messages on the Voice Agent socket;
- do not remove REST session creation before measurement;
- do not rewrite all prompts during audio stabilization;
- do not upgrade Composio packages without migration analysis;
- do not change read/write confirmation semantics casually;
- do not add retries to writes without idempotency.

---

# 30. External Documentation to Verify During Implementation

Use current official documentation, not cached examples.

## Deepgram

Voice Agent configuration:
https://developers.deepgram.com/docs/configure-voice-agent

Voice Agent Settings / `agent.greeting`:
https://developers.deepgram.com/docs/voice-agent-settings

Prompting Voice Agents:
https://developers.deepgram.com/docs/prompting-voice-agents

Voice Agent message flow / barge-in:
https://developers.deepgram.com/docs/voice-agent-message-flow

LatencyReport:
https://developers.deepgram.com/docs/voice-agent-latency-report

UpdateSpeak:
https://developers.deepgram.com/docs/voice-agent-update-speak

Flux TTS voices:
https://developers.deepgram.com/docs/flux-tts/voices

Voice Agent LLM models:
https://developers.deepgram.com/docs/voice-agent-llm-models

Function calling:
https://developers.deepgram.com/docs/voice-agents-function-calling

## Composio

Sessions overview:
https://docs.composio.dev/docs/how-composio-works

Configuring Sessions:
https://docs.composio.dev/docs/configuring-sessions

Direct tools to Sessions migration:
https://docs.composio.dev/docs/migration-guide/direct-to-sessions

Meta tools:
https://docs.composio.dev/toolkits/meta-tools

Documentation changes quickly. Verify exact SDK method names and payloads against the installed/current version before coding.

---

# 31. Coding Standards for This Work

- Preserve existing feature/module boundaries unless a phase explicitly requires restructuring.
- Prefer typed request/result models.
- Avoid `dict[str, Any]` across major internal boundaries when a stable contract can be modeled.
- Keep provider-specific Composio slugs below the semantic capability layer.
- Make async cancellation behavior explicit.
- Keep write-side effects traceable.
- Use structured logging.
- Redact secrets.
- Avoid huge raw tool payloads in LLM context.
- Keep functions focused.
- Add docstrings where lifecycle/cancellation semantics are non-obvious.
- No silent exception swallowing around critical state transitions.
- No arbitrary sleeps as race-condition fixes.
- No retry loops around writes without idempotency.
- Tests must assert behavior, not merely status code `200`.

---

# 32. Required Communication Protocol With Reviewing Engineer

After every phase, answer in this structure:

## A. Phase Completed

State exact phase and sub-items completed.

## B. Files Changed

| File | Symbols | Reason |

## C. Behavior Before

Explain the prior runtime path.

## D. Behavior After

Explain the new runtime path.

## E. Tests

List tests and results.

## F. Runtime Verification

Include sanitized logs/timings/events.

## G. API/SDK Assumptions Verified

List the exact Deepgram/Composio behaviors verified from current docs/runtime.

## H. Deviations

Anything implemented differently from this document and why.

## I. Issues Found

New defects discovered.

## J. Not Changed

Explicitly list adjacent areas intentionally left untouched.

## K. Recommended Next Step

Recommend only the next phase; do not implement it.

---

# 33. Immediate Instruction

**Begin with PHASE 1 only.**

Do not implement the remaining phases yet.

However, use the complete architecture in this document to avoid Phase 1 changes that would conflict with:

- semantic tool routing;
- Composio Sessions;
- Flux TTS;
- voice selection;
- companion prompting;
- memory;
- LangGraph complex-task execution.

When Phase 1 is complete, return the required report and stop.
