# mockjuice — Vision & Context

> Read this for a feel of the product, not as a literal spec or source of truth to
> follow mechanically. It exists to build intuition/taste for judgment calls, not
> to be quoted back or treated as exhaustive requirements. When it conflicts with
> an explicit instruction in the moment, the explicit instruction wins.

mockjuice combines a toy-like, high-end visual brand with a ruthlessly efficient
practice engine, turning a stressful driving theory test into a seamless,
satisfying experience. Target audience: 17-24 year olds on TikTok, prepping for
their UK theory test.

**Positioning philosophy**: gamified in look and feel, deliberately — not the
shallow version (arbitrary points, forced streaks, badges bolted onto a boring
task) but "game feel": interaction design tuned for momentum and psychology.
Every competitor licenses the identical DVSA question bank, so the questions are
commoditised — execution of the interface is the product. Closest real-world
comparison: Duolingo, but for the theory test. Branding takes inspiration from
Innocent Drinks — "juice" is a metaphor for the knowledge needed to pass, and the
"5 a day" idea underpins the 5-category structure.

**Two jobs that must both be true at once, never traded off**:
- *Gamified UI = acquisition hook.* Toy-like vector aesthetic + mascot make a
  stressful, commoditised product look premium enough to choose over a
  competitor with an identical question bank.
- *Gamified UX = retention engine.* Zero-latency answer-to-next-question loops,
  tactile micro-feedback (haptics, snappy button response), and visual mastery
  tracking (colour-coded strength/weakness, not a spreadsheet of percentages)
  reduce the cognitive drain of studying.

**The governing rule**: if an element delays the user from reaching the next
question — even half a second — cut it. If it makes them want to answer the next
one immediately, invest more in it. This is why the mascot lives on the
periphery (home screen, milestone celebrations) and never gates the core answer
loop — correct/wrong mascot reactions were deliberately dropped from in-practice
for this reason.

**Core structure**: a visual journey path with 5 categories, each with its own
brand colour — theory, highway code, road signs, mock test, explore. Theory is
the flagship and only fully built category: 784 real DVSA questions across 14
topics, with practice modes (all-questions, not-seen-yet, flagged-for-review,
weakest-first by mastery score derived from real answer history). The other four
categories are visually present and unlocked but intentionally inert —
placeholders, not yet real features.

**Design system**: see [DESIGN.md](DESIGN.md) for the actual documented system
(flat, light-mode-only, cartonCream background, custom rounded typeface,
semantic colour rules — red for errors, gold for rewards, blue for primary
actions). Currently mid-refinement: closing a "feels bland" gap vs. Duolingo-tier
polish — custom-animated mascot (idle done; correct/wrong/big-win/onboarding-wave
in progress via Masko), custom iconography, a palette punch-up, and a full
micro-interaction pass, all filtered through the zero-latency rule.

**Business model**: onboarding is the highest-stakes screen — where paid
conversion happens. Onboarding is tuned to build trust/warmth before the payment
ask (mascot wave placed early), then the actual paywall moment is kept clean and
mascot-free.

**Current build state**: theory is functional end-to-end (questions, scoring,
mastery tracking, streaks, readiness %). Highway code, road signs, mock test,
explore exist on the map with no real content yet — that's the honest state of
the product today.
