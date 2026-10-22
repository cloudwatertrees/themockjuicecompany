# Scene trace progress (A home screen + B continuation)

Working copy: `tools/scene-trace/work` (relocate.sh). Python deps installed with `pip --use-deprecated=legacy-certs`
(the sandbox blocks macOS trust evaluation: OSStatus -26276). skia-python installed; pipeline import unchanged.

## 2026-10-19 — Seam: STOPPED (planned stop, awaiting generated band)

Inputs: `A.png` (937x1678, untouched), `B_orig.png` (937x1679; trimmed to 1678 in the seam tool).

Measured (cream-path mask): A last row path x 385–664 (279), right brown bank 664–738. B row 0 path 399–511 (112),
no right bank; 162 wide at row 20, 247 at row 60. Raw join mean |dL| 33.79 (x 81–856) vs A's own neighbour-row
differences in its bottom 200 rows: mean 2.44, p95 3.12, max 3.94.

Two attempts, same path-anchored horizontal warp (dl −11.0, dr +151.8, smoothstep over 260 rows, displacement held
constant to x 81/856 and tapered outside the visible range):

| Attempt | Join method | Seam mean abs. dL | Visual (1x and 3x) |
|---|---|---|---|
| 1 | Poisson gradient blend over 120 rows, row −1 pinned to A | 3.41 (pass) | Fail: brown/pink stain over the grass where A's bank meets B, left foliage and rock colour bleed |
| 2 | A's bottom rows mirrored + min-error DP cut (rows 4–59) + Poisson | 0.84 (pass) | Fail: mirrored rock, bush, pine and a doubled pebble; the bank stops on a cut line |

Both pass the row metric only because row 0 is forced to A's colours; the structural mismatch (rock/bank/pine
in A, canopy/grass/bushes in B) moves a few rows down. Root cause is content, not alignment: A's 74 px brown bank
has no counterpart in B's top 200 rows.

Best crops: `seam/best_join_1x.png`, `seam/best_join_3x.png` (attempt 2). Exports for the generator:
`seam_ref.png` (A's bottom 400 rows), `seam/inpaint_canvas.png` + `seam/inpaint_mask.png`, prompt in
`seam/generator_prompt.md`.

Next: generated band → replace B rows 0–219 → `seam/joincheck.py` → save `B_seam.png` → trace.

## 2026-10-19 — Phase 1: finished with the attempt-2 seam (B_seam.png = seam/B_cut.png)

Pipeline: `i2s/` (copy of image2swiftui with colour-class layers: `hf_groups.py`, `masks.py`; canvas-size background;
optional Skia import). 10 layers, back to front: meadow, pathEdges, path, water, rocks, wood, foliage, conifers, accents,
flowers. Swift via `work/tools/extract.py` → `v2_gen_swift.py` (layer list adjusted; live file as template) and
`work/tools/gen_ext.py` (extension wrapper kept; seamGround/topBounce/bottomBounce recomputed).

| Screen | Regions | Skia | Python model | Real SwiftUI render (1x, 937x1678) | Swift file |
|---|---|---|---|---|---|
| A | 20k | 0.9746 | 0.9748 | 0.9744 | 5.8 MB |
| A | 40k | 0.9811 | | | 9.5 MB |
| A | 80k | 0.9846 | | 0.9848 | 15.6 MB |
| **A** | **100k** | 0.9850 | | **0.9853** (MAE 1.30/1.19/1.06) | **18.4 MB** |
| B | 20k | 0.9759 | 0.9759 | 0.9755 | 5.4 MB |
| B | 40k | 0.9827 | | | 9.0 MB |
| **B** | **80k** | 0.9862 | | **0.9863** (MAE 1.38/1.25/1.17) | **15.0 MB** |

Release harness (iPhone 16 Pro sim, 402x874 @3x, cold process): A parse 88 ms, raster/first draw 310 ms,
footprint 89 MB; B parse 65 ms, first draw 240 ms, footprint 72 MB. Redraw 0.1 ms.

App: built with `app/build_app.sh` (swiftc + simctl; xcodebuild cannot write DerivedData/info.plist in the sandbox,
the simulator build tool cannot read the Desktop project, #Preview macros and actool cannot run: previews stripped from
a build copy, no Assets.car). Launched, scrolled top → join → bottom: renders; join shows attempt-2 flaws.

## 2026-10-19 — Phase 2 ended: gate FAILED, best seam applied

Two rounds (log: `seam/rounds/log.md`). Final seam `B_seam.png` = `seam/r02_composite` (bank continues into the
mushroom island's cliff). Gate: (1) seam row 1.35 PASS, five edit boundaries over 4.96 FAIL (object-outline cuts);
(2) structure: no mirrored/doubled objects, bank ends naturally, but smudged path cream near the lamp arm and a
pink band left of the bank remain; (3) blind test 6/6 joins identified FAIL; (4) phone 1x: continuous at a glance,
the lamp-arm smudge is visible. Rendered phone join (393x852 @3x): last/first row |dL| 2.05 vs top screen's own
neighbour-row p95 1.76.

## Phase 3: retrace and single-file merge

B retraced from the final seam at 80k regions: real SSIM 0.9862 (MAE 1.38/1.25/1.17). A unchanged (100k, 0.9853).
`ios/mockjuice/Views/Components/ForestPathIllustration.swift` is now the only art file (33.4 MB): ForestPathIllustration
is the whole scroll (LazyVStack of two screens, same Layout rule, async per-screen raster cached only while on screen,
evicted on disappear), ForestPathLayers(ids, screen:), ForestPathArt (Screen, LayerID, Layout, ScreenRaster,
topGround/seamGround/topBounce/bottomBounce), TopScreen/BottomScreen data. ForestPathExtension.swift deleted;
HomeSceneView shows only ForestPathIllustration. Generator: `work/tools/gen_merged.py` + `merged_head.swift`.
Pre/post merge (`work/merge/host.sh`): per-screen renders pixel-identical (0 px differ), SSIM 0.9853/0.9862 both,
phone join rows identical.

Verified after merge: Release compile 22 s, Debug 18 s (whole app, swiftc); app launched, scrolled top → join →
bottom in the iPhone 16 Pro simulator. Release host (402x874 @3x class, cold): top 222 ms, bottom 193 ms per-screen
raster at phone size incl. parse; footprint 109 MB with both screens' data parsed and four rasters made.

## 2026-10-19 — Rework request: scroll fault fixed; trace-quality investigation

Scroll fault (solid ground colour below the join): the bottom screen's raster started only when the LazyVStack built
that segment (as it scrolled in) and was evicted on disappear; an unoptimised build needs 0.4–1.1 s per screen on the
Mac simulator, several times that on a phone. Fix (merged_head.swift → ForestPathIllustration.swift): one shared
`ForestPathArt.Rasters` store (ObservableObject; @Observable needs a macro the sandbox cannot run) starts every
screen as soon as the size is known, top screen first, each in 4 strips drawn as they finish, and keeps both
(~24 MB at 3x). Strips stacked = whole screen within 1/255; Release strip 50–63 ms each. Verified: fling into the
bottom screen right after launch (Debug, simulator) shows it fully drawn.

Trace quality (quality/): crop of B 937x600 at the full-trace density (28.6k regions).
| Config | SSIM | edge F1 (rec/pre) | detail (HF energy vs source) | grad SSIM | size |
|---|---|---|---|---|---|
| c0 current | 0.9852 | 0.968 (0.956/0.981) | 0.886 | 0.9530 | 5.3 MB |
| c1 edge-aware merging (new, EDGE_TAU=12) | 0.9851 | 0.966 | 0.886 | 0.9525 | 5.3 MB |
| c2 edge-aware + smoothing 0.6 + tolerance 0.15 | 0.9861 | 0.968 | 0.885 | 0.9540 | 7.1 MB |
Zoom crops (quality/evidence.png): geometry matches the source within ~1 px; the soft, blotchy look is the 937 px
source itself, shown at 1.52x on the phone. Tracing changes cannot add sharpness the source lacks. Stopped for a
decision on the source (see report).

## 2026-10-19 — 2x upscaled sources, tuned trace, installed

Upscale: Real-ESRGAN RealESRGAN_x4plus_anime_6B (github.com/xinntao/Real-ESRGAN v0.2.2.4, SHA-256 f872d837…, loaded
weights_only) run locally on CPU by `upscale/upscale.py`: A over B_seam stacked and upscaled as one image (4x, Lanczos to
2x), split into `upscale/out/A2x.png`, `B2x.png` (1874x3356). ~8 min.
Trace settings (crop tests in quality/, metric quality/qmetrics.py incl. path/cap boundary error and wobble):
INPUT_SCALE=2 SUPERRES=2 TRACE_TOLERANCE=0.2 CONTOUR_SMOOTHING=0.7, 80k regions. Cap boundary error 1.51 → 0.74 px
(2x px) vs the old settings on the same 2x crop; tighter (0.12/0.4, 0.08/0.25) gave 0.66 px at 2x the data size —
rejected. Edge-aware merging (EDGE_TAU) measured no gain; left off.
Results (real renders, Release host): phone 3x SSIM vs 2x source: top 0.9885, bottom 0.9875 (vs original 1x PNGs 0.960 /
0.958 — the upscaler redraws small details). Rendered phone join |dL| 1.66 vs top's own neighbour-row p95 1.91.
ForestPathIllustration.swift 47.3 MB (A 24.0 + B 23.3 MB data); Debug app compile 16 s; Release per-screen phone raster
206 / 221 ms; footprint 126.5 MB. Simulator: fling into the bottom right after launch shows it fully drawn.
Before/after sheet: quality/before_after.png. Disk was full (183 MB free); regenerable scratch deleted.

## 2026-10-19 — Mushrooms back to the reference; path consistency edits

The 2x upscale (previous entry) redrew details (a dark sliver between the caps, changed spots, a stray spot on the small
cap); the trace reproduced them. Reverted to tracing the original reference with the original settings: on the 1x
source the cap boundary error is 0.12 px (tighter fitting 0.13 px for +56% data — no gain). A unchanged (A100k).
Path edits on B (`seam/path_fix.py`, output `seam/r03_path/`, now `B_seam.png`; previous saved as out/B_seam.r02.png):
tone of B's whole path matched to A's (delta -5/-2/0 RGB; removes the line at the join), left path edge continued from
A's verge to the lamp island with meadow grass from A and A's own edge tufts (removes the bite and smear), cut shadow
shapes in B rows 0–150 cleaned (incl. the pink smudge by the bank), 7 A-style pebbles shrinking into B's first 450 rows.
Source seam row 1.55. B retraced (80k, original settings): real SSIM 0.9861; A 0.9853. File 33.4 MB.
Path width: A's last stretch ~300 px, B ~225 px (114 px pinch at the waterfall pool) — the two illustrations differ;
not changed (would need warping B's scenery sideways). Rendered phone join |dL| 2.19 vs top's own p95 1.76.

## 2026-10-19 — Mushroom outlines fixed in the tracer; B's path widened

Cause of the mushroom "blobs": the reference's soft 1-2 px anti-aliasing ramps (spot/cap, cap/grass) were traced as thin
sliver regions with irregular outlines, and soft shading split into flat regions with hard internal edges.
Pipeline changes (i2s/): `slivers.py` dissolves AA slivers pixel-wise into the best-fitting neighbour before boundary
placement (16-19k per screen); `meshfill.py` gives every region >= 40 px a least-squares bilinear mesh-gradient fill
(the renderer's `*W H` format, 4-unit cells); edge-aware merging on (EDGE_TAU=10); contour smoothing 1.5 (2.5 made spots
angular). Settings: MESH=1 MESH_MIN=40 MESH_CELL=4 EDGE_TAU=10 CONTOUR_SMOOTHING=1.5, 100k regions per screen.
Path: `seam/widen.py` widens B's path by 25% of its width (cap 50 px per side), sides moved as rigid blocks, smoothed
along y, ramped in from the join; mushroom rows put 85% of it on the left so the island stays on screen. Width mean
223 -> 275 px (A's lower path ~300), pinch 111 -> 150 px. Max shear 0.31 px/row locally; no visible lean.
Real SSIM: top 0.9819, bottom 0.9843 (crisp edges instead of soft ramps cost ~0.003). File 32.3 MB, footprint 103 MB,
Debug compile 16 s. Simulator verified (fling across the join, mushrooms, path). Rendered phone join 2.10 vs p95 1.75.
