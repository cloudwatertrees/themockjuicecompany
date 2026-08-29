# mockjuice Design System

## Color Palette

| Token | Name | Hex | Role |
|---|---|---|---|
| `.deepForest` | Deep Forest | #182D09 | Primary text color, used everywhere |
| `.spring` | Spring | #7C9D45 | Secondary background — input fields, selected states, subtle section grouping |
| `.macaw` | Macaw | #1CB0F6 | Primary actions/links/CTAs — buttons, tappable text, active tab indicators |
| `.bee` | Bee | #FFC800 | Highlights/rewards/badges only — streaks, achievement badges, notification dots. Never used for text. |
| `.cardinal` | Cardinal | #FF4B4B | Errors/destructive only — form validation, delete actions, failed states |
| `.cartonCream` | Carton Cream | #F8F3E6 | Primary background color — the default background for every screen in the app, no exceptions |
| `.innocentWhite` | Innocent White | #FFFFFF | Secondary text color on non-cream surfaces (dark/colored backgrounds); also the surface color for cards/sheets/elevated elements |

These roles are directional principles, not an exhaustive list of every allowed use — apply the same logic to new cases that aren't explicitly listed above.

## Illustration Colors

Colors representing real-world objects (traffic lights, scenery/terrain, traffic signs) are exempt from the brand palette above and live in a separate `MJTheme` category — see `Theme.swift` under `// MARK: - Illustration Colors`. These should still be named tokens, never raw hardcoded RGB values in view files.

Current illustration tokens:

| Token | Depicts |
|---|---|
| `.trafficRed` / `.trafficAmber` / `.trafficGreen` | Traffic light lamps |
| `.grassLight` / `.grassDark` | Roadside grass verges |
| `.hillLight` / `.hillDark` | Background hills |
| `.treeFoliage` / `.treeFoliageDark` / `.treeTrunk` | Trees along the path |
| `.roadAsphalt` / `.roadMarking` | Road surface and lane markings |
| `.signPost` / `.signFaceBlue` / `.signFaceWhite` | Roadside traffic signs |

## Journey Node Category Colors

Each of the 5 major categories on the journey path map has its own distinct primary color, so users can visually distinguish categories at a glance rather than every node looking the same:

| Category | Color Token | Status |
|---|---|---|
| theory | `.deepForest` / `.spring` (green family) | Functional |
| highwayCode | `.macaw` | Not yet functional — visual only |
| roadSigns | `.bee` | Not yet functional — visual only |
| mockTest | `.cardinal` | Not yet functional — visual only |
| explore | `.cartonCream` / `.deepForest` (neutral — cream surface, forest text/icon) | Not yet functional — visual only |

The 5 categories are: theory, highwayCode, roadSigns, mockTest, explore. There is no hazardPerception category — disregard any earlier reference to it.

Implemented via `JourneyNode.categoryColor` / `categoryForeground` in `Theme.swift`, consumed by `JourneyNodeView`. Every standard badge carries a `deepForest.opacity(0.15)` ring so the cream `explore` node stays legible against the cream screen. The theory node keeps its distinct "sticker" treatment (translucent `deepForest` circle that the road reads through) rather than a flat `spring` fill — that is intentional and still inside theory's green family.

Non-functional nodes keep their existing disabled treatment (`locked` fill + lock icon + faded label). The category color is applied only when unlocked, so a locked node reads as neutral.

**Known gap (not a design decision):** the four non-theory nodes are described above as non-functional, and they have no real content — but `JourneyPathView.handleNodeTap` currently *does* route them to placeholder screens, and highwayCode/roadSigns/mockTest also call `progress.completeNode(..., score: 10)` on tap. That behaviour predates this pass and was deliberately left untouched. It should be resolved (either genuinely no-op the taps or build the content) before release.

## Core Design Principle: No Dark or Gradient Surfaces

Every screen background is flat `cartonCream`. No gradients, no dark surfaces, no tinted background overlays, anywhere in the app. Visual interest comes from illustration, color-coded icons/buttons/badges, and typography — never from the background itself. (Reference: Duolingo's actual light-mode home screen is flat white with zero background variation; all character comes from the path illustration and icons layered on top.)

Elevated surfaces (cards, sheets, the bottom nav bar, modal overlays) use flat `innocentWhite` with `deepForest` text and a soft `deepForest` low-opacity shadow — never a dark or gradient fill.

Surfaces converted from dark/gradient to flat light during this pass: the journey readiness card, the "section 1" header card, the settings gear button, the bottom tab bar, the quiz header bar (which carries the progress bar), the whole video-download intro screen, and its skip-confirmation dialog. The only remaining dark fills are deliberate small elements on light ground: the option-letter circles (A/B/C/D), the score capsule on the theory node, the traffic-light housing, and the road illustration itself.

Modal scrims are `deepForest.opacity(0.45)` rather than black.

This is a light-mode-only system. System dark mode is not supported.

## Semantic Decisions Log

Judgment calls made while implementing the palette, recorded so they don't get re-litigated:

- **Red is no longer the CTA color.** Previously every primary button was the logo red (`appleRed`/`coral`). Under this system `cardinal` is reserved for errors/destructive only, so all primary CTAs moved to `macaw` — onboarding "next/let's drive", theory intro "continue", start mock test, start download, continue/finish in the quiz, results "continue", download-clip. `cardinal` now appears only on genuinely destructive or failure affordances: reset all data, "skip for now" in the download warning, wrong answers, and failed states.
- **Streak / "hot" indicators** — previously `.orange`, now `.bee` (hot streak, ace driver). Streaks are a reward/highlight, exactly `bee`'s role.
- **Achievement badge accent** — previously `.purple`, which has no palette equivalent. Resolved to `.macaw` (sharp mind, flagged finder); the progress-style badges (halfway, mock ready) use `.spring`. Rationale: `macaw` is the only remaining chromatic token not reserved for errors (`cardinal`) or backgrounds (`spring`), and it stays visually distinct from the gold streak badges.
- **Mastery scale** — mastered (≥70%) = `spring`, developing (≥40%) = `macaw`, needs work = `cardinal`, untouched = `deepForest.opacity(0.25)`. Uses existing palette roles rather than inventing a gradient.
- **Question flag icon** — `bee` when flagged. Flagging is a save/highlight action, not an error.
- **Flagged-questions review CTA** — `macaw`, not `bee`. `bee` is explicitly never used behind text, and a gold button needs dark text that then reads as low-contrast; the gold stays on the icon/badge only.
- **Glass/liquid effects** — the highlight sheen stays `innocentWhite.opacity(...)`, but the shadow/well tone uses `deepForest.opacity(...)` instead of raw black, so even incidental shading is palette-derived. Every card shadow in the app is now `deepForest` at low opacity.
- **Locked/disabled state** — a single opaque forest-tinted neutral, `locked` (#C9CFC0), rather than an alpha-based token. Kept opaque so call sites can still apply their own `.opacity(_:)` without compounding alpha unexpectedly. Faded text/icons use `deepForest.opacity(...)` directly.
- **Material/blur surfaces removed** — the unused `adaptiveGlass` helper (`.ultraThinMaterial`) was deleted; it was the last translucent-material surface and conflicted with the flat-surface principle. Remaining gradients are all *within* a single token's own shades (progress-bar fill, results gauge, onboarding horizon glow) — never a background.

This file is the source of truth. If a future change conflicts with it, update this file in the same change — do not let code and doc drift apart.
