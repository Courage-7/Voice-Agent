# Execution contracts and the active runtime

Updated 18 September 2026. This document defines the interfaces for the readiness plan; it does not claim that every consumer already implements them.

## Active path

The browser opens the FastAPI voice WebSocket. `RealtimeClientSession` forwards audio and control events to `DeepgramVoiceAgentSession`. Deepgram's Voice Agent service drives the live speech/LLM turn loop and invokes the common tool registry. The registry calls domain tools, which use the provider adapters.

The complex-task engine is a separate Python workflow loop reached through a registered tool. The LangGraph graph is an alternative path exercised by unit tests; it is not the orchestrator for live Deepgram turns. Keep it out of the live path until its purpose and acceptance tests justify enabling it.

## Contracts for subsequent phases

| Contract | Required fields and invariant | Completion phase |
|---|---|---|
| Actor context | Server-derived Clerk subject and `session_id`; no tool argument may override identity. | 7 |
| Tool outcome | Explicit `status`: `succeeded`, `failed`, `needs_confirmation`, `needs_clarification`, `cancelled`, `uncertain`, or `unavailable`; optional structured `data`, `error`, and provider receipt. If legacy `success` remains, it is true only for `succeeded`. | 2 |
| Pending action | Action ID, canonical tool name, immutable validated arguments/hash, owner, session, expiry, approval state, and consumed state. Knowing an action ID alone is not approval. | 2–3 |
| Workflow checkpoint | Task ID, owner, session, goal, ordered steps, current step, prior results, pause reason, and pending action/clarification handle. Only completed prerequisites feed later steps. | 3–4 |
| Connection | Provider, owner, connection ID, and explicit `pending`, `active`, `failed`, `expired`, or `revoked` status. Presence of a record does not establish an active connection. | 4, owner binding in 7 |
| Spoken output | Short spoken text plus a separate machine envelope retaining status, IDs, and continuation handles. Compression cannot authorize, complete, or lose an action. | 2 |

Result and workflow status names currently differ between modules. Normalize at provider and domain boundaries during Phases 2–4; do not introduce another independent orchestration framework to solve this mismatch.

## Runtime configuration

The root manifest and `uv.lock` are authoritative for development, CI, and Docker. The nested backend manifest remains compatible for package builds; a regression check prevents its dependencies and build requirements from drifting.

`ENVIRONMENT=production` requires Deepgram, Groq, Composio, PostgreSQL `DATABASE_URL`, and Clerk issuer plus a JWT verification key or JWKS URL. Startup also requires built frontend files, initialized tool/model clients, and a connected database pool. Clerk owns passwordless email-code delivery; the backend verifies its short-lived session JWTs.

`ENVIRONMENT=testing` ignores local environment files. Pytest clears credentials, resets shared state, blocks unexpected external connections, and requires explicit fake-provider fixtures for successful external operations. Live vendor evaluations must be run separately with test accounts and explicit credentials.

`ENVIRONMENT=demo` also ignores local environment files and disables initialization of external providers. The UI displays a demo notice; in-memory state is temporary. Missing providers outside demo mode must not manufacture OAuth URLs or model responses.

`FRONTEND_DIST_PATH` supplies one frontend location to both the page router and static asset mounting. Installed images set it explicitly. Playground HTML is packaged with the backend wheel.

## Remaining boundaries

Production mode is a configuration choice, not a release approval. Validate Clerk session verification, WebSocket rejection paths, and database ownership enforcement against the deployed origin before launch. Per-process ledgers and best-effort persistence also do not satisfy restart or multi-worker guarantees.
