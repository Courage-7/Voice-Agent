# VoiceAgent project guidance

## Product and interface mode

- This project is a voice-first web application.
- Treat the application interface as an **Operate** surface: task clarity, state visibility, accessibility, and reliability outrank decoration.
- Treat a future marketing or landing page as a separate **Persuade** surface with its own brief.

## Design workflow

- Use `$impeccable` as the primary workflow for every frontend design, build, redesign, critique, audit, or polish task.
- Before creating the first interface, complete `$impeccable init` and save the product truth in `PRODUCT.md`. Do not invent the audience, business claims, core voice workflow, or privacy promises.
- Do not merge several design skills into competing creative directions. Use `$ui-ux-pro-max` only for targeted design-system research, accessibility checks, or implementation guidance. Use `$design-taste-frontend` only for expressive marketing pages, portfolios, or landing-page work.
- Preserve approved decisions in `PRODUCT.md`, `DESIGN.md`, and the relevant surface brief. A later task must read those files before changing the visual world.

## Voice-interface quality floor

- Make every voice state explicit in words, not only through color, glow, motion, or a waveform. Account for idle, microphone permission, ready, listening, processing, speaking, interrupted, muted, reconnecting, unavailable, and error states where applicable.
- Never make voice the only way to understand or operate the product. Provide visible controls, keyboard access, focus states, status announcements, and a text alternative appropriate to the product.
- Treat microphone access, recording, retention, and transmission as trust-critical moments. Explain what is happening at the point of action and never imply privacy guarantees that have not been confirmed.
- Respect reduced-motion preferences. Waveforms and ambient animation must communicate state without causing distraction, layout shift, or continuous expensive rendering.
- Design real empty, loading, permission-denied, offline, timeout, and recovery experiences rather than demonstrating only the happy path.

## Completion standard

- A frontend task is unfinished until the rendered interface has been inspected at desktop and mobile sizes, interactions have been exercised, accessibility basics have been checked, and one bounded correction pass has been completed.
- For Impeccable builds, follow its detector and finish-review workflow. Report unresolved findings honestly instead of calling the work complete.
