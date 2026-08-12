# VAgent Interface Design

## Visual world

VAgent is a dark, quiet, futuristic operating surface. Its signature is a luminous blue-violet voice orb made from moving particle lines, balanced against a spacious reading canvas. The interface is precise and restrained: one authored motion moment, code-native typography and controls, and no decorative dashboard clutter.

## Desktop composition

- True wide desktop workspace, designed around a 16:9 viewport.
- Compact VAgent identity at the top-left.
- Collapsed navigation is a single vertically centered 48px trigger on the far-left rail.
- Activating the trigger opens a narrow overlay menu; it must not resize the voice or results regions.
- Voice stage occupies the center-left and is separated from results by a subtle one-pixel vertical rule.
- Results use an open, independently scrollable surface rather than a rounded card.
- No microphone, keyboard, handset, call, or bottom-dock controls.

## Palette

- Canvas: `#02040b`
- Canvas lifted: `#050814`
- Primary text: `#f4f7ff`
- Secondary text: `#9bc9df`
- Muted UI text: `#aeb8cd`
- Divider/border: `rgba(151, 167, 205, 0.20)`
- Electric blue: `#1768ff`
- Violet: `#7a5cff`
- Active surface: `rgba(95, 78, 190, 0.18)`

## Typography

- Use the bundled open-source `Manrope Variable` face with system sans fallbacks.
- Results heading: 44–52px desktop, weight 500, tight tracking.
- Body/results: 18–22px with generous line-height.
- Navigation/control text: 15–16px, weight 450–500.
- Status text: 18–20px in secondary blue.

## Iconography

- Use the official `lucide-react` package.
- Outline icons, `strokeWidth={1.7}`, rounded caps/joins, 20–22px.
- Inventory: `AudioWaveform`, `Boxes`, `Sparkles`, `Wrench`, `Puzzle`, `ScrollText`, `Settings`, `ChevronLeft`, `ChevronRight`, `ExternalLink`.
- No emoji, Unicode glyph icons, generated pseudo-icons, or keyboard icon.

## Navigation

- Menu order: Voice, Capabilities, Skills, Tools, Plugins, Logs, Settings.
- Voice is active by default.
- A divider separates Plugins from Logs and Settings.
- Rows are at least 44px high and support pointer, keyboard, focus, and selected states.
- Escape and outside click close the menu; the trigger exposes `aria-expanded` and `aria-controls`.

## Motion

- The voice orb continuously breathes and responds as the single signature animation.
- Use soft scale, rotation, line drift, and luminance changes—not layout movement.
- Navigation uses a short exponential ease-out reveal.
- Under `prefers-reduced-motion: reduce`, freeze ambient orb animation and remove nonessential transitions.

## Responsive behavior

- Desktop: two content regions plus the collapsed left rail.
- Tablet/narrow desktop: preserve the left rail and stack results below the voice stage when width becomes insufficient.
- Mobile: compact top identity and menu trigger, smaller orb, results in normal document flow; no bottom navigation or duplicate voice controls.

## Accessibility

- Keep the textual voice state visible.
- Use semantic buttons and links, visible focus rings, 44px targets, and appropriate labels.
- Navigation selection must not rely on color alone.
- Results links remain underlined on hover/focus and include external-link icon components.
