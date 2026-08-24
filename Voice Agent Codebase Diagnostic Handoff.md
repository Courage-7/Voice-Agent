I need you to perform a **read-only technical audit of this voice-agent codebase** for another senior AI/ML/voice-systems engineer who will review your findings and send implementation guidance back through me.

This is a diagnostic handoff.

## Critical rules

- DO NOT modify, refactor, format, delete, rename, or create application files.
- DO NOT install or upgrade dependencies.
- DO NOT implement fixes yet.
- DO NOT alter prompts, Deepgram configuration, Composio configuration, frontend audio code, LangGraph/orchestration code, or environment files.
- You may run safe/read-only inspection commands and existing tests if appropriate.
- Never expose API keys, OAuth tokens, secrets, credentials, connection strings, or private environment values.
- Environment variables may be reported by NAME only.
- Do not infer behavior from filenames alone. Trace actual call paths.
- Do not tell me what you think the architecture probably does. Tell me what the code demonstrably does.
- If something cannot be determined, explicitly write `UNKNOWN`.
- Include exact file paths, classes/functions/components, configuration objects, and approximate line numbers where practical.
- Include short relevant code snippets when they materially help explain the implementation.
- Do not dump entire files.

The problems currently observed are:

1. The predefined/default voice greeting has noticeable latency.
2. Connected Composio toolkits are not always used correctly for the user's request.
3. The agent sometimes chooses the wrong action from a connected toolkit.
4. When another request is made during or shortly after an existing response/tool call, agent speech can overlap.
5. Barge-in/interruption behavior does not appear completely reliable.
6. We want to evaluate/migrate to Deepgram Flux TTS where appropriate.
7. We want the user to be able to select among Deepgram voices.
8. The agent currently feels too rigid/tool-like. The desired experience is more conversational and companion-like while still being accurate and effective at executing tools.

The project currently uses several Composio toolkits/accounts, including Gmail, Outlook, calendar-related apps, Perplexity AI, and several others. Determine the exact currently configured toolkits from the code/config rather than assuming this list is exhaustive.

---

# A. CODEBASE MAP

Start with a concise architecture map.

Report:

- repository root structure
- backend framework
- frontend framework
- Python version
- Node version if applicable
- package/dependency manager
- important dependency versions
- Deepgram SDK/package and version
- Composio SDK/package and version
- LLM provider(s)
- current LLM model(s)
- orchestration framework, if any
- WebSocket implementation
- audio capture/playback libraries
- state management libraries
- persistence/database implementation
- testing stack

Then identify the main files responsible for:

- application startup
- voice WebSocket/session initialization
- Deepgram connection
- Deepgram Settings creation
- STT
- turn detection
- LLM invocation
- system/personality prompt
- function/tool calling
- Composio integration
- tool discovery
- toolkit selection
- action selection
- tool execution
- conversation state
- audio output/playback
- interruption/barge-in
- greeting
- frontend voice UI
- session persistence
- logging/observability

Provide a text architecture flow such as:

Microphone
→ frontend audio transport
→ backend
→ Deepgram STT
→ conversation/orchestration layer
→ LLM
→ tool router
→ Composio
→ tool result
→ LLM
→ TTS
→ frontend playback

But make the diagram match what the application ACTUALLY does.

---

# B. TRACE APPLICATION STARTUP AND DEFAULT GREETING

Trace the greeting from connection initiation until the user actually hears audio.

Answer:

1. Where is the greeting text defined?
2. Is it defined in:
   - Deepgram `agent.greeting`
   - system prompt
   - application code
   - frontend
   - an LLM-generated first turn
   - somewhere else?
3. Does an LLM request occur before the greeting can be spoken?
4. Does LangGraph/orchestration initialization occur before greeting playback?
5. Are Composio tools loaded before the greeting?
6. Are connected accounts fetched before greeting playback?
7. Are database/session operations blocking the greeting?
8. Does the frontend wait for some state before enabling playback?
9. Are there unnecessary awaits in this startup path?
10. Is audio buffering contributing to perceived greeting latency?

Provide the exact sequence as:

T0 ...
T1 ...
T2 ...
...

Where possible, identify existing timestamps/log events that could be used to measure each stage.

Also report whether Deepgram latency reports or equivalent voice timing telemetry are currently captured.

---

# C. DEEPGRAM CONFIGURATION

Locate the exact Deepgram Voice Agent `Settings` payload or equivalent configuration.

Report the CURRENT values for:

### Listen/STT

- provider
- API version
- model
- language
- endpointing/turn detection configuration
- `eot_threshold`
- `eager_eot_threshold`
- `eot_timeout_ms`
- VAD settings
- any interruption-related settings

Mark anything that is absent.

### Think/LLM

- provider
- model
- endpoint
- prompt/system instructions source
- tool/function definitions
- temperature
- token/output limits
- timeout configuration
- streaming configuration

### Speak/TTS

Report:

- provider
- Deepgram API version
- model
- voice
- speed
- expressivity if present
- encoding
- sample rate
- output transport
- whether TTS is streamed
- whether Flux TTS `/v2` is currently being used
- whether Aura `/v1` is currently being used
- whether TTS is instead delegated to another provider

If the project currently references Flux, report every Flux-related configuration or code path.

Do not change it yet.

---

# D. VOICE SELECTION SUPPORT

Determine how difficult it would be to make Deepgram voices user-selectable.

Inspect whether:

- TTS model is hard-coded
- it comes from environment variables
- it comes from backend settings
- it comes from frontend state
- it is persisted per user/session
- it can currently be changed at runtime

Identify the exact place where a selected voice would need to flow:

Frontend voice selector
→ API/session configuration
→ backend state
→ Deepgram Settings / UpdateSpeak
→ persisted preference if appropriate.

Also determine whether the current WebSocket implementation can send Deepgram `UpdateSpeak` messages during a live conversation.

Do not implement it.

Report whether any existing UI already resembles a voice/model selector that could be extended.

---

# E. AUDIO PIPELINE AND OVERLAPPING SPEECH

This is a high-priority investigation.

Trace agent audio from the moment TTS audio is produced until the browser/device plays it.

Identify:

- audio queues
- buffers
- MediaSource/AudioContext/WebAudio usage
- HTML audio usage
- playback manager
- WebSocket audio frames
- streaming chunks
- queue ownership
- current-turn identifiers
- response identifiers
- generation identifiers
- AbortControllers
- cancellation tokens
- asyncio Tasks
- background tasks
- locks
- event listeners
- cleanup functions

Then determine EXACTLY what happens when:

1. Agent is speaking.
2. User begins speaking.
3. `UserStartedSpeaking` or equivalent event is received.
4. A new user turn is created.
5. An existing LLM generation is still running.
6. An existing tool request is still running.
7. Old TTS chunks arrive after interruption.
8. A new TTS response begins.

Answer these questions explicitly:

- Does user barge-in immediately stop local playback?
- Is the playback buffer cleared?
- Is current TTS generation interrupted?
- Is current LLM generation cancelled?
- Are late audio frames discarded?
- Can audio from two assistant turns coexist in the playback queue?
- Does audio carry a `turn_id`, `speech_id`, generation, or equivalent identifier?
- Can stale audio from an older turn be distinguished from current audio?
- Are multiple audio playback instances created?
- Are multiple WebSocket listeners accidentally registered?
- Can multiple assistant response tasks run concurrently?
- Can an acknowledgement response and final tool response overlap?
- Can reconnections produce duplicate event handlers?
- Is `UserStartedSpeaking` handled?
- Is `AgentAudioDone` handled?
- Is Deepgram `Interrupt` used anywhere?
- Is `SpeechInterrupted` used anywhere?
- Is `text_spoken` / `text_remaining` tracked anywhere?

Give your most evidence-backed explanation for how overlapping audio could currently occur.

Do NOT implement a fix.

---

# F. TURN STATE MACHINE

Determine whether the project has an explicit conversational state machine.

Look for states equivalent to:

- CONNECTING
- GREETING
- LISTENING
- USER_SPEAKING
- END_OF_TURN
- THINKING
- TOOL_ROUTING
- TOOL_EXECUTING
- SPEAKING
- INTERRUPTED
- CANCELLED
- COMPLETED
- ERROR

If one exists, document it.

If one does not exist, explain how state is currently inferred or coordinated.

Identify any race conditions where two states/tasks can be active simultaneously.

If LangGraph is involved, provide:

- graph definition path
- nodes
- edges
- conditional edges
- state schema
- reducers
- checkpointing
- async execution pattern
- tool node(s)
- conversational node(s)
- interruption handling
- how graph execution relates to Deepgram voice events

---

# G. COMPOSIO ARCHITECTURE

This section must be detailed.

Find every Composio integration point.

Report:

- Composio SDK version
- initialization code
- API client/service wrapper
- user identity mapping
- connected-account mapping
- auth configuration strategy
- toolkit loading
- tool loading
- action loading
- tool execution
- errors/retries/timeouts
- result normalization
- any caching

Determine whether the implementation uses:

- Composio Sessions
- `tools.get(...)`
- direct tool execution
- toolkit-scoped discovery
- meta-tools
- another Composio pattern

List the exact toolkits/apps currently configured or referenced.

Do NOT expose credentials.

For each toolkit, report whether the code loads:

- the whole toolkit
- selected actions
- dynamic actions
- cached definitions

If there is a global tool limit such as `20`, identify it.

Determine approximately how many tool/action schemas are exposed to the LLM at once.

This is important.

---

# H. TOOL ROUTING AND ACTION SELECTION

Trace these example requests through the actual system:

### Example 1
"Do I have anything tomorrow morning?"

Expected category: calendar read/search.

### Example 2
"Reply to John's latest email and tell him I'll send the document tomorrow."

Expected category:
- email search/read
- identify message/thread
- email reply/write

### Example 3
"Search Perplexity for the latest information about X."

Expected category: Perplexity/search.

For each, explain:

User transcript
→ intent interpretation
→ toolkit selection
→ tool/action selection
→ argument construction
→ account selection
→ execution
→ result returned
→ final response

Answer:

- Who chooses the toolkit?
- Who chooses the action?
- Is toolkit selection separate from action selection?
- Does one LLM choose everything at once?
- Are all tool schemas included in one prompt?
- Are action descriptions sufficient?
- Are required parameters visible?
- How are missing parameters handled?
- How are tool results passed back?
- Can the model execute multiple sequential actions?
- Can it reason over a first tool result before choosing the second tool?
- Can it recover from a failed action?
- Can it accidentally choose Outlook when Gmail is intended?
- How is the target account/provider disambiguated?
- What happens when Gmail and Outlook expose semantically similar actions?
- What happens if the user says "my email" without specifying provider?
- How does the application know which connected account belongs to this user?
- Are write operations treated differently from read operations?
- Are confirmations required for destructive or externally visible actions?
- Is idempotency handled for send/create/update actions?

Identify concrete reasons why the model could be selecting the wrong toolkit or wrong action.

Rank these causes by likelihood, but base the ranking on code evidence.

---

# I. TOOL EXECUTION VS VOICE EXECUTION

Determine whether tool execution blocks the voice pipeline.

Trace what happens during a slow operation.

For example:

User:
"Check my calendar for tomorrow."

Does the application:

A.
Wait silently
→ execute tool
→ generate answer
→ speak

B.
Speak an acknowledgement
→ execute tool
→ speak final answer

C.
Perform some other sequence

If acknowledgements exist, determine:

- who generates them
- whether they have their own TTS turn
- whether they can overlap with the final result
- whether tool completion can trigger speech while acknowledgement speech is still playing

Inspect async task management around tool execution carefully.

---

# J. SYSTEM PROMPT / PERSONALITY / COMPANION BEHAVIOR

Find all prompts controlling agent behavior.

Provide their paths and explain how they are assembled.

Do NOT paste sensitive or extremely long prompts verbatim. Relevant sections are enough.

Determine whether the current prompt instructs the agent to be:

- concise
- formal
- task-oriented
- terse
- neutral
- conversational
- warm
- proactive
- expressive
- companion-like

Look for instructions that may unintentionally make responses robotic.

Also identify:

- max response length
- token limits
- terse-answer constraints
- tool-call formatting instructions
- repeated "how can I help?" patterns
- fixed acknowledgements
- canned tool messages
- generic error messages

Report how conversation history is maintained.

Determine whether the agent has:

- short-term conversational memory
- session memory
- persistent preferences
- user profile/preferences
- prior tool result memory
- previous-turn awareness
- conversation summaries
- context trimming

The desired eventual behavior is a capable conversational companion, not merely a voice interface over APIs.

That means we eventually want behavior such as:

- natural conversational transitions
- contextual acknowledgement
- continuity across turns
- remembering what was just discussed
- concise responses when appropriate but not mechanically terse
- varied phrasing
- natural follow-up questions when genuinely useful
- smoothly integrating tool use into conversation
- avoiding robotic statements such as "Executing tool Gmail action..."
- not repeatedly announcing capabilities
- handling corrections naturally
- responding appropriately to interruption
- sounding engaged without pretending to be human
- avoiding unnecessary filler

For now, assess how far the existing implementation is from that target.

DO NOT rewrite the prompt yet.

---

# K. CONVERSATION MEMORY AND CONTEXT

Trace exactly what is sent to the LLM on every turn.

Report:

- system prompt
- previous user messages
- previous assistant messages
- tool calls
- tool results
- interrupted assistant responses
- transcript
- summaries
- persisted state

Determine whether an assistant message is recorded as fully spoken even if the user interrupted halfway through it.

This is particularly important.

Also determine whether tool outputs become unnecessarily large and whether context growth could contribute to latency.

---

# L. OBSERVABILITY

Report current logging/tracing for:

- speech received
- end of turn
- LLM started
- first LLM token
- tool selected
- tool started
- tool finished
- TTS requested
- first audio byte
- playback started
- playback completed
- user interruption
- cancellation
- errors

Check for Deepgram `LatencyReport` handling.

Check whether latency can currently be decomposed into:

STT latency
LLM first-token latency
tool-selection latency
tool-execution latency
LLM final-response latency
TTS first-byte latency
client playback latency
total turn latency

Report what is missing.

---

# M. ERROR HANDLING

Find handling for:

- disconnected Composio account
- expired OAuth
- missing scopes
- wrong tool arguments
- tool timeout
- tool HTTP error
- LLM timeout
- Deepgram disconnect
- TTS error
- WebSocket reconnect
- interrupted tool call
- duplicate action execution

Explain whether failures can leave the agent in an invalid state such as permanently THINKING or SPEAKING.

---

# N. TEST COVERAGE

Identify existing tests covering:

- Deepgram connection
- greeting
- Flux/Aura TTS
- audio interruption
- barge-in
- stale audio
- concurrent turns
- Composio toolkit loading
- tool selection
- sequential tool calls
- Gmail
- Outlook
- Calendar
- Perplexity
- write-action safety
- voice selection
- WebSocket reconnect
- conversation state

Report test names and paths.

Run existing relevant tests if safe and report results.

Do not repair failing tests.

---

# O. FINAL RESPONSE FORMAT

Return your findings in this exact high-level order:

## 1. Executive Summary

No more than 15 bullets.

## 2. Architecture

Actual current runtime architecture.

## 3. Important File Map

Table:

| Concern | File | Symbol/Class/Function | Purpose |

## 4. Current Voice Configuration

Exact Deepgram STT/TTS/LLM configuration.

## 5. Greeting Lifecycle

Exact call sequence and likely latency sources.

## 6. Turn and Audio Lifecycle

Explain listening → thinking → tool → speaking → interruption.

## 7. Overlapping Audio Investigation

Evidence, race conditions, most likely cause(s).

## 8. Composio Integration

How toolkits, accounts, tools and actions are actually loaded/executed.

## 9. Tool Routing Investigation

Why wrong toolkit/action selection may occur.

## 10. Connected Toolkits

Exact current toolkit list found in the project/configuration.

## 11. Voice Selection Feasibility

Where dynamic Deepgram voice selection would be integrated.

## 12. Companion/Personality Architecture

Current behavior and what currently makes it rigid.

## 13. Memory and Context

How conversations/tool results are retained.

## 14. Latency and Observability

Existing measurements and missing measurements.

## 15. Tests

Relevant coverage and results.

## 16. Confirmed Problems

Use:

- `[CONFIRMED]`
- `[STRONG EVIDENCE]`
- `[POSSIBLE]`
- `[NOT FOUND]`

Do not blur those categories.

## 17. Questions You Still Cannot Answer

Only genuinely unresolved items.

## 18. Recommended Intervention Points

IMPORTANT:

Do not implement anything.

Simply identify the exact files/components where fixes would likely need to happen.

## 19. Raw Evidence Appendix

Include compact snippets, paths, configuration excerpts, logs/test results necessary for the reviewing engineer to independently assess your conclusions.

The report is being passed to another engineer, so optimize for technical precision and evidence rather than explanation for a beginner.