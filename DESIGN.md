# Shinra Voice Agent Design System

Version: 1.0
Status: active design direction
Scope: `frontend/src/**`

This file is the visual and content contract for Shinra. Use it for every frontend change. The product is a browser voice assistant that helps a person complete real work through speech, tools, and connected services. The interface must make the current state, next action, and result easy to understand.

## Product Character

Shinra should feel like a calm, capable operations desk for a voice assistant, not a sci-fi dashboard and not a marketing landing page.

The visual personality is:

- Quietly technical
- Human and direct
- Precise under pressure
- Warm without being cute
- Focused on work, not spectacle

The UI should communicate: "I know what is happening, I will tell you what happened, and I will ask before I change anything."

## Design Diagnosis

The existing interface currently overuses:

- Glassmorphism and blur
- Floating capsule and pill navigation
- Decorative grids, glows, and waveform atmosphere
- All-caps telemetry language
- Marketing claims presented as live product facts
- Abstract labels such as "Neural Matrix", "LPU Telemetry", and "Initialize Voice Session"
- Multiple competing dashboards on one screen
- Tiny text and dense decorative badges

Do not extend these patterns. Replace them gradually with clear product language, flat surfaces, stronger information hierarchy, and controls that describe the work they perform.

## Visual Direction

Use a light, editorial operations-console aesthetic:

- Warm off-white page canvas
- Ink-black primary text
- Deep charcoal for the active voice surface
- One restrained coral accent for the main action and attention states
- Muted blue only for links and selected informational states
- Green, amber, and red only for semantic status
- Hairline borders and very limited shadow
- No decorative gradient backgrounds
- No decorative blur behind controls
- No nested cards
- No full-page dark mode unless the voice studio specifically needs a dark audio surface

Reference influences were studied from public design-system analyses for ElevenLabs, Composio, Cal.com, and Claude on getdesign.md. These are inspiration only. Do not copy their branding, logos, exact layouts, or text.

## Color Tokens

Define tokens centrally. Components must use semantic tokens instead of raw hex values.

```css
:root {
  --color-canvas: #f7f5f0;
  --color-surface: #ffffff;
  --color-surface-muted: #eeece7;
  --color-surface-dark: #1d1d1b;
  --color-surface-dark-elevated: #292925;
  --color-ink: #1d1d1b;
  --color-body: #45443f;
  --color-muted: #77746d;
  --color-faint: #9b978e;
  --color-hairline: #dedbd3;
  --color-focus: #bd624b;
  --color-action: #b95740;
  --color-action-active: #974631;
  --color-link: #245d83;
  --color-success: #28734d;
  --color-warning: #94651f;
  --color-danger: #a33e3e;
  --color-on-dark: #f7f5f0;
  --color-on-action: #ffffff;
}
```

Color rules:

- Use `--color-action` for one primary action per view.
- Do not use purple or blue gradients as a default brand treatment.
- Do not use color alone to communicate status. Pair it with text or an icon.
- Status colors are functional, not decorative.
- All normal text must meet WCAG AA contrast of at least 4.5:1.
- Focus rings use `--color-focus` with a 3px visible outline.

## Typography

Use expressive but readable type. Prefer a humanist or editorial display face for headings and a neutral sans for interface text. Do not use Space Grotesk, Plus Jakarta Sans, or a generic system stack as the default merely because they are convenient.

Recommended pairing:

- Display: `DM Serif Display` or `Fraunces`, weight 400
- Interface/body: `Manrope` or `IBM Plex Sans`, weights 400, 500, 600
- Data/code: `IBM Plex Mono`, weight 400, 500

If external font loading is unavailable, use a local fallback with the same character: Georgia for display, Arial-like sans for interface, and a monospace fallback for data.

Type scale:

| Token | Size | Line height | Use |
|---|---:|---:|---|
| display | 48px | 1.05 | One primary product statement only |
| page-title | 32px | 1.15 | View title |
| section-title | 22px | 1.3 | Major section |
| component-title | 17px | 1.35 | Panel or row title |
| body | 16px | 1.5 | Main explanatory text |
| body-small | 14px | 1.5 | Supporting text |
| label | 12px | 1.4 | Form labels and metadata |
| data | 13px | 1.45 | IDs, durations, timestamps |

Rules:

- Never use all-caps for full sentences.
- Use sentence case for navigation, buttons, headings, and descriptions.
- Keep labels short, literal, and useful.
- Do not use negative letter spacing.
- Body text must not be smaller than 14px on desktop or 16px on mobile.

## Layout

Use a stable app shell:

- Header: 64px, left-aligned product name, primary navigation, account actions
- Main content: max-width 1200px, aligned to a consistent 24px grid
- Desktop gutters: 32px
- Tablet gutters: 24px
- Mobile gutters: 16px
- Major section spacing: 48px
- Component spacing: 8px, 12px, 16px, 24px, 32px
- Mobile breakpoint: 640px
- Tablet breakpoint: 768px
- Desktop breakpoint: 1024px
- Wide content cap: 1280px

Do not center every screen. The voice workspace can center the active listening control, but history, connectors, settings, and task results should use left-aligned editorial layouts.

Do not put cards inside cards. Use full-width bands for page sections and cards only for genuinely repeated records, tool results, or modal surfaces.

## Navigation

Primary navigation uses text plus familiar icons:

- Voice
- History
- Connections
- Skills

Use a normal header or compact sidebar. Do not use a pill-in-pill navigation dock. The active item uses ink text and a 2px accent rule or a restrained filled state.

Mobile navigation becomes a simple menu or bottom navigation with no more than five top-level items.

## Voice Workspace

The voice workspace is the product's primary screen.

Required hierarchy:

1. Session state: `Ready`, `Listening`, `You are speaking`, `Thinking`, `Assistant speaking`, `Needs attention`, or `Offline`.
2. One large microphone/session control.
3. Current spoken exchange or transcript.
4. Active task progress, if a tool is running.
5. Recent result or approval request.
6. Secondary controls for transcript, history, and connections.

The primary control labels are literal:

- `Start voice`
- `Stop voice`
- `Pause listening`
- `Resume listening`

Do not use `Initialize Voice Session`, `Neural Voice Matrix`, `Gateway`, `LPU Telemetry`, or `Full-Duplex Execution` as user-facing labels.

Audio visualization is allowed only when it communicates microphone input or assistant playback. Use a restrained waveform or level meter with a static fallback. Never use a decorative animated orb, breathing glow, or infinite equalizer as the main visual.

## Task and Tool States

Every tool interaction must have a visible state:

- Preparing
- Waiting for confirmation
- Running
- Completed
- Could not complete
- Needs more information
- Connection unavailable

Each state includes:

- What the assistant is doing
- Which service is involved
- What the user can do next

Example:

- `Draft ready. Send this email to Maya?`
- `Checking your Google Calendar...`
- `Email sent to Maya. Message ID available in details.`
- `I could not send the email because Gmail is disconnected. Reconnect Gmail and try again.`

Never show a success state because a request was attempted. Show success only when the provider confirms it.

## Connections

Connections are a practical account-management view, not a colorful logo wall.

Each connection row contains:

- Service name
- Connection status
- Account or workspace identifier when safe to show
- Last checked time
- One clear action: `Connect`, `Reconnect`, or `Disconnect`

Use service icons consistently, but do not make every connector a saturated colored tile. Use color in the icon or a small status marker, not as the entire card background.

Connection statuses use plain language:

- Connected
- Needs reconnecting
- Connection failed
- Not connected
- Checking connection

## History and Results

History is a readable list, not a telemetry wall.

Each conversation row shows:

- Date and time
- Short user request summary
- Outcome status
- Duration only when useful

Task results should prioritize the outcome and next action. Technical IDs, provider receipts, and raw payloads belong behind `Details`.

## Controls and Components

Buttons:

- One primary button per view.
- Minimum 44px touch target.
- Radius: 6px for standard controls, 10px for larger feature controls, full radius only for status dots or circular icon buttons.
- Use icons from the existing Lucide dependency when they improve recognition.
- Icon-only buttons require an accessible label and a tooltip.
- Disabled controls must explain why they are disabled when the reason is not obvious.

Inputs:

- Always use visible labels.
- Use semantic input types and autocomplete.
- Keep input height at least 44px.
- Put validation beside the relevant field.
- Preserve entered data after recoverable errors.

Cards:

- Use a 1px hairline border.
- Use white or muted surface fills.
- Use one low-elevation shadow tier only where a surface must separate from the canvas.
- Do not use blur or translucent glass for ordinary panels.

Drawers and dialogs:

- Use for secondary context, not primary navigation.
- Have a visible close button and Escape support.
- Trap focus while open.
- Explain destructive actions before confirmation.

## Content and Voice

Copy should sound like a capable assistant, not a game HUD or an ad.

Use:

- `Start voice`
- `Your connections`
- `Recent conversations`
- `Waiting for your confirmation`
- `Try again`
- `Reconnect Gmail`
- `No conversations yet`

Avoid:

- `Neural`
- `Quantum`
- `Matrix`
- `LPU Telemetry`
- `Operator`
- `Initialize`
- `Activate protocol`
- `Experience the future`
- Unsupported performance claims such as `<480ms` unless the value is measured and contextualized

Descriptions explain user value or current state. They must not explain the design, list features as marketing copy, or narrate what an icon means.

## Motion

Motion should explain state changes:

- 150-250ms for hover, focus, and pressed states
- 250-400ms for drawers and panels
- Animate opacity and transform, not layout dimensions
- Stop or reduce animation when the session is idle
- Respect `prefers-reduced-motion`
- Never use continuous animation only to make an empty screen feel alive

## Accessibility and Responsive Rules

- Keyboard navigation must follow the visual order.
- Focus must always be visible.
- All important status updates use an accessible live region.
- Never rely on color, hover, sound, or motion alone.
- Support 375px mobile width without horizontal scrolling.
- Preserve readable 16px mobile body text.
- Reserve space for async transcript, task, and connection content to avoid layout shift.
- Do not hide essential navigation labels on tablet widths.

## Implementation Rules for AI Coding Agents

Before changing a frontend component:

1. Identify the user's task on that screen.
2. Identify the current state and the next possible action.
3. Use existing tokens and components before adding new ones.
4. Prefer a smaller number of meaningful elements over decorative panels.
5. Write literal UI copy before styling it.
6. Check mobile layout, keyboard focus, loading, empty, error, and success states.
7. Do not introduce new gradients, glass panels, pill navigation, abstract telemetry labels, or decorative orbs without an explicit product reason.

When replacing existing UI, preserve behavior and API contracts. Remove visual noise without removing access to transcripts, connection state, tool results, authentication, or session controls.

## Current Refactoring Direction

Refactor in this order:

1. Replace the centered capsule header with a normal app header.
2. Rewrite the landing view as a direct voice entry screen with one clear action.
3. Simplify the voice workspace around session state, microphone control, transcript, and task outcome.
4. Replace telemetry-as-marketing panels with an optional technical details view.
5. Restyle connectors as an account list with honest connection states.
6. Restyle history as a readable conversation list.
7. Replace abstract labels and unsupported performance claims across the frontend.
8. Consolidate colors, typography, spacing, radius, and motion into semantic CSS tokens.

## Sources and Inspiration

- https://getdesign.md/what-is-design-md
- https://getdesign.md/elevenlabs/design-md
- https://getdesign.md/composio/design-md
- https://getdesign.md/cal/design-md
- https://getdesign.md/claude/design-md
- https://designmd-store.com/docs/quickstart
- https://designmd-store.com/docs/format/sections
- https://designmd-store.com/docs/best-practices/writing-for-ai

These references informed the structure and principles only. Shinra's product behavior and user needs remain the source of truth.
