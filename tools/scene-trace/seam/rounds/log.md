# Seam rounds

Gate: (1) numeric — seam row <= 3.1, edit boundaries <= B's own neighbour-row p95 (4.96, corrected by the user after
round 1); (2) structure; (3) blind test (<= 4 of 6 joins identified); (4) phone 1x continuity.

## Round 0 (before Phase 2): attempt 2, mirror + DP cut — seam 0.84; structure FAIL (mirrored rock, bush, pine, doubled pebble, bank cut line)

## Round 1: three variants in parallel (sheets: r01_join1x.png, r01_phone1x.png, r01_join3x.png)

| Variant | Seam row | Failing edit boundaries (limit 4.96) | Structure |
|---|---|---|---|
| va_taper | 4.10 FAIL | pine 5.30, bushes 11.99, left 5.17, boulder 6.11, leftverge 5.76 | Bank ends abruptly beside a cream notch; faint tone bands across the path at 3x; verge tone step |
| **vb_join** | **1.25** | pine 5.08, left 9.41, boulder 9.18 (object outlines) | **Best**: bank flows into the island cliff. Flaws: leaf-size jump (left, y 12–30), cut pink path shading (y 0–12), half-cut pebble, grainy cliff base, pine brightness line at y 0, flat-bottomed fringe at left path edge |
| vc_transplant | 2.09 | left 13.63, bank 6.13, lip 8.15 | Bank stops at y≈100 with a ragged cream gap; serrated lip edge |

Gate tooling fixes in this round: phone crops now resample A+B as one image (separate resizing drew a line at the join);
3x sheet narrowed to 1492 px.

Round 2 plan: refine vb_join; join agent on x >= 395, taper agent on x < 395 (on vb_join's image); composite at x 395.

## Round 2: vb_join_r2 (x >= 395) + vl_left_r2 (x < 395), composited at x 395 → r02_composite
Both agents stopped on an API rate limit after writing outputs; constraints verified (no edits outside their half,
none below row 499). Seam row 1.35 ok; boundaries over 4.96: L_behind 18.60, L_fringe 11.25, L_shade 14.43,
L_seam 6.12, R_pine 5.05 (left-side edits follow canopy outlines). Structure: marginally better than round 1 (left
canopy overlaps A's bush irregularly). Rounds used: 2 of 15 (stopped by the user's resume instructions).

Blind test (blind/, seed 11, fresh reviewer, crops only): identified 6 of 6 joins → FAIL (limit 4).
Reviewer's cues: cream tone bands across the path at the join, smudged path cream and stone remnants near the lamp
arm (left path edge, x ≈ 300–420, y 0–60), a pinkish smudge band left of the bank. Key: blind/key.txt.
Applied as the best fallback seam: B_seam.png = r02_composite/B_seam.png.
