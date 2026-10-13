# Paused: fit the full forest scene to the phone

Problem: the 937x1678 art is 9:16, iPhone 16 Pro is 9:19.5, so aspect-fill crops 17.6% of the width (back trees 49%,
pond 29%, log 20% hidden). Full art in frame needs a 937x2037 canvas (359 px taller, about 180 px top and bottom).

## State
- `ios/mockjuice/Views/Components/ForestPathIllustration.swift` currently holds the **new v2 art** (937x1678, uncommitted).
  Old art: `tools/forest-v2/backup/ForestPathIllustration.phaseB.swift`.
- Pipeline already accepts any canvas size (follows `ref/ref.png`); see `README.md` for the run order.
- Taller image from ChatGPT: `Assets.xcassets/forestpathtest.imageset/Extended Whimsical Forest Path.png` (854x1840).
  It is a redraw, not an extension: the original sits in it at scale 0.865, offset (29, 231), match 0.69.
  Its pond is partly covered by a tree on the left; bridge, rocks and style are otherwise equivalent.
- `scripts/v2_composite.py` (V2_WARP=1) keeps the original pixels in the middle and adds the generated strips:
  **bottom seam is clean; top seam is not** (path borders break near it).

## Options when resuming
1. Top-seam fixes: restrict the seam to the path interior; warp harder before cutting. (~30 min)
2. Fallback A: original + the clean bottom strip only.
3. Fallback B: trace the generated image whole (no seams, pond partly covered): about 45 min compute + checks.
4. Cheapest: fit-to-width in `HomeSceneView` and let the next section fill the 154 pt gap.
