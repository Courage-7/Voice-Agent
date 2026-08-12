# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React, TypeScript, and Vite. The deployment target will be settled after the forthcoming `PLAN.md`.

## Users

The primary user is the project's owner, using the product as a personal voice agent.

## Product Purpose

Provide one voice-first interface for working with a personal agent and its expanding set of capabilities, skills, tools, and plugins. The interface should make speaking to the agent primary while keeping its activity, results, and controls understandable on screen.

## Positioning

The product's mechanism is a personal voice session that can invoke modular skills, tools, plugins, retrieval, and agentic actions rather than acting only as a conversational transcript.

## Product Identity

- Product name: `VAgent`.
- The identity combines a compact original voice-orb mark with the `VAgent` wordmark.
- The standalone mark also serves as the collapsed desktop navigation trigger.

## Operating Context

- Personal web application.
- Voice is the primary interaction channel; the screen supplies state, control, context, and results.
- The primary surface is intentionally simple: one large circular voice-reactive motion visualization plus a dedicated region for findings or results returned to the user.
- The desktop presentation uses a wide 16:9 workspace rather than scaling up the portrait composition.
- A fuller product and implementation plan will be supplied later in `PLAN.md`.

## Capabilities and Constraints

- Modular capabilities, skills, tools, and plugins.
- Agentic behavior and multi-step action execution.
- Retrieval-augmented generation (RAG), interpreting the user's mention of "rad" as RAG; confirmation remains open.
- Skills, tools, plugins, and other capability areas need accessible management entry points. Keep those controls visually secondary to the voice workspace, while low-level retrieval mechanics and execution traces remain out of the primary interaction surface.
- The voice visualization should be round, visibly react to speech, and carry a futuristic technical character.
- The visible experience should expose the current voice state, the circular motion visualization, returned findings or results, and only the controls necessary for the immediate interaction.
- The voice interaction is an agent workspace, not a phone call; avoid handset, hang-up, or other telephony controls and metaphors.
- Provide access to Voice, Capabilities, Skills, Tools, Plugins, Logs, and Settings without crowding the primary voice interaction.
- On desktop, keep the management navigation collapsed by default to one vertically centered icon trigger; activating it expands the labeled menu as progressive disclosure.
- On desktop, the persistent Voice navigation entry owns access to the voice interaction; do not duplicate microphone or keyboard buttons at the bottom of the workspace.
- Use a coherent production icon library for interface controls; do not use keyboard imagery, emoji, Unicode glyphs, or generated pseudo-icons.
- The findings surface is a single output area; it does not need separate Transcript and Result tabs.
- The desktop findings surface is a large, independently scrollable rich-results canvas that can present long text, hyperlinks, images, files, and other returned content.
- The surface adapts by state: the voice visualization is large while listening, then contracts into a compact persistent indicator when long findings arrive so the result receives most of the viewport.
- Long findings must be readable and scrollable without displacing persistent navigation or the current voice-state indicator.
- Product name, providers, integrations, data sources, permissions model, storage behavior, and deployment target remain open.
- The draft must not imply unconfirmed integrations, completed actions, or commercial claims.

## Evidence on Hand

No product assets, production data, benchmarks, customer claims, or implementation evidence are currently available. Demonstration content in concept visuals is illustrative and must not be treated as live product data.

## Product Principles

- Voice first, never voice only.
- Make agent state and consequential actions legible.
- Keep capability management accessible but subordinate to the primary voice interaction.
- Put the user in control of permissions, interruptions, and execution.
- Allow the interface to grow as new skills, tools, and plugins are added.

## Accessibility & Inclusion

Project-level requirements call for textual status alongside sound, animation, waveform, or color; visible controls; keyboard operation; focus visibility; appropriate announcements; a text alternative to voice; and reduced-motion behavior.
