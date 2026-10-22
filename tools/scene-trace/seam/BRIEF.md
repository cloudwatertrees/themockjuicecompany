# Seam variant brief (shared by every variant agent)

Goal: an edited copy of illustration B whose top band continues illustration A seamlessly, so that A (top screen) and
B (scrolling in directly below it) read as one painting. You produce one variant in your own folder.

## Files (repo root /Users/laverath/Desktop/themockjuicecompany; work in tools/scene-trace/seam/)

- Python: `/Users/laverath/Desktop/themockjuicecompany/tools/scene-trace/work/venv/bin/python` (numpy, scipy,
  scikit-image, opencv-python-headless, Pillow). Use `$TMPDIR` for scratch. Write scripts to files and run them.
- `../A.png` 937x1678 RGB. **Never modify A.** A's last row (y = 1677) sits directly above B's first row (y = 0).
- `base/B_trim.png` 937x1678: the original B.
- `base/B_warp.png`: B after the path-anchored horizontal warp (from `seam.py`, function `warp_B(A, B, 260)`): B's cream
  path edges at row 0 moved to A's last-row path edges (left x 385, right x 664), easing back to the original by row 260.
  **Start from this warp** (load it, or call `seam.warp_B`). You may re-tune the warp's band length if you say why.
- `gate.py VARIANT_DIR`: numeric gate + crops (join_1x, join_3x, phone_1x, phone_3x). Run it after every change.
- `r00_attempt2/`: the previous best (mirror + cut) and its crops, for comparison. Its flaws: mirrored rock, bush, pine
  and a doubled pebble; the bank stops on a cut line.

## Hard rules

- Edit only B's top 500 rows (y < 500). Everything else stays identical to `base/B_warp.png`.
- Use the art's own pixels: clone/transplant patches from A or from B (translation, small scale, small rotation,
  per-patch colour/contrast matching). **No mirroring or flipping of recognisable objects. No global blends or
  cross-fades between A and B. No smearing, no blur over structure, no Poisson/gradient fills over large areas.**
- Every edit is blended in with a short feather (2-6 px) after matching local mean and contrast at its edge.
- Save each edit's alpha as a float32 937x1678 mask (1 = fully edited pixel) in `VARIANT_DIR/edits.npz`
  (`np.savez(path, bank=..., grass=..., boulder=..., pine=...)`; names are yours). gate.py measures the boundary
  of each one.
- Crops you save must be <= 1500 px wide.
- Do not touch anything outside your variant folder (no other variants, no Swift, no git).

## Scene facts (design space; x across 937, y = 0 at the join, positive downwards into B)

- Phone-visible range is x 81–856; judge everything there.
- Path: A's last row cream x 385–664. Warped B's path at row 0 matches.
- A's right bank (brown earth, with lighter oval pebbles and a darker scalloped outer edge) runs along the path's right
  side through A's last 200 rows, x ≈ 664–738 at the join. Right of it: a thin grass verge (x ≈ 738–760), then A's large
  dark-teal pine (x ≈ 760–937), cut by A's bottom edge.
- Warped B at the top right (y 0–120, x ≈ 680–937): leafy teal bushes with yellow/white flowers, a teal pine at the far
  right; below them the red mushroom island. The island's earth cliff (B's own bank) begins at the island's top-left
  corner (warped ≈ x 600, y 125; original ≈ x 575, y 120) and runs down beside the path to y ≈ 420. Another bank: the
  lamp island left of the path (warped ≈ x 330–430, y 150–230) ends at its corner by the path. **These island corners
  are how this artist ends a bank**: the cliff face tapers to a point under an overhanging grass lip.
- Left: A's lavender-grey boulder (x ≈ 120–260) is cut by A's bottom edge, partly hidden by light-green bushes in front.
  Warped B's top-left (y 0–60, x 0–360) is the light-green canopy of a large tree.

## Gate (the variant must aim to pass all of it)

1. gate.py NUMERIC PASS: the A-to-B seam row mean |dL| <= 3.1 (A's own neighbour-row p95). Each edit boundary's mean
   |dL| <= B's own neighbour-row p95 over rows 0..499 of the warped B (about 4.9; gate.py prints the exact value).
   Pass/fail is decided mainly on items 2-4; the numbers are a floor, not the target.
2. Structure: no doubled or mirrored objects, no cut lines, no colour stains, path edges smooth and continuous, the bank
   ending naturally.
3. A blind reviewer must not be able to tell join crops from interior crops of A.
4. 1x phone crops look continuous.

## Report (keep it short, plain text)

- What you did (method per edit, parameters), files written.
- gate.txt contents.
- Honest flaw list from your own look at join_1x, join_3x, phone_1x, phone_3x (name each: doubled/mirrored object,
  cut line, stain, hard edge, path-edge break, unnatural bank end), with coordinates.
