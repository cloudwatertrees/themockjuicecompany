# SwiftUI Reconstruction

How to turn an illustration (PNG) into a layered, pure-SwiftUI vector view at high fidelity, with named layers you can
animate or restyle. This is the only process doc: read it fully before starting, follow the gates, and do not
re-derive anything listed under "Dead ends".

Evidence labels used below: **[verified]** reproduced or measured by a session and re-run on 2026-10-10;
**[reported]** stated by an earlier session, not re-run; **[estimate]** my estimate, not measured.

## 1. What exists

| Stage | Code | State |
|---|---|---|
| 1. Trace: image to layered shapes to a Swift file | `tools/image2swiftui/` (`pipeline.py`) | **[verified]** rebuilt `324a66d`'s file byte for byte. Never run on a second image. |
| 2. Verify: real render plus metrics | `tools/image2swiftui/harness/` (quick), `tools/forest-regrade/scripts/` (full) | **[verified]** full harness reproduced SSIM 0.9851 and dE00 0.55 on the committed file |
| 3. Refine (optional) | `tools/forest-regrade/scripts/tools/pb_*.py` | **[verified]** on the forest. Needs existing vector shapes as input. |
| 4. Integrate screens (scroll) | not built | see section 9 |

Lineage: Stage 1 produced `324a66d` (SSIM 0.9822, crisp). Phase A (colour regrade to a new reference) and Phase B (quality pass)
refined that file into `16f964a` (SSIM 0.9851). Stage 3 consumes Stage 1's data format (one shape per line,
`RRGGBB <path>`), so Stage 1 output can feed Stage 3 **[estimate: same line grammar, and `extract.py` splits a Swift file into
per-layer data; not yet tried]**.

## 2. Ask the user once, before any work

1. **Fidelity or small file?** Default: maximum fidelity, about 10k regions, 110k segments, 3.4 MB, SSIM 0.982. A small
   hand-editable file (about 1k shapes) tops out near SSIM 0.91.
2. **Layer names.** The elements to animate or restyle (fox, door, bridge, ...). The order is back to front.
3. **Edges.** Default crisp. Changing this after tracing wasted hours last time.

## 3. Run (Stage 1)

    cd tools/image2swiftui && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/python pipeline.py art.png --out Art.swift --regions 10000     # about 80 s on 8 cores

Run scripts from a file, never stdin (the worker pool needs an importable main). Steps and defaults:

1. Felzenszwalb over-segmentation (`scale=5, sigma=0.3, min_size=3`): about 93k pieces on 937x1678.
2. **Name layers** (`semantic.py`, `masks.py`, `hf_groups.py`): colour class x hand-placed region polygons. Layer order in
   `hf_groups.GROUPS` is the z-order. **Image-specific; see section 8.**
3. Merge within each layer, cheapest first, by the error of an affine colour model (`dendro.py`). Cut at N regions.
4. Re-place boundaries at 4x against the bicubic-upsampled reference (`superres.py`): about +0.008 SSIM.
5. Trace each region to cubic Beziers (`hf_vec.py`, `bezier.py`): occlusion-aware (a region extends under what is painted
   over it, so no gaps), 0.25 px tolerance on visible edges, looser where hidden, contour smoothing sigma 1.0 at 4x, corner
   detection, merging of smooth-joined segments. Fills: flat, or a 2-stop linear gradient.
6. Write Swift (`emit_swift.py`): each layer is one multi-line string, one shape per line, `RRGGBB <path>` or
   `RRGGBB RRGGBB x0 y0 x1 y1 <path>`; path is SVG data with relative `c` at 0.1 px precision; a single-pass byte reader parses
   it once. Plus a full-canvas background rectangle.
7. Soft zones (`softzones.py`): optional blurred pass kept only 4 px or more from hard colour edges. **[verified]** +0.0008 SSIM.
   Phase B dropped it for mesh fills. **Known bug (read from code, not run): `--no-soft` writes a file that does not compile**
   because the template still references `softZoneData`. Leave the soft pass on until fixed.

## 4. Verify (every stage, every time)

Gate order. Do not claim a score from an earlier gate.

1. **Skia preview** (printed by `pipeline.py`): quick sanity only.
2. **Real SwiftUI render:** `harness/render.sh Art.swift out.png` then `score.py ref.png out.png`. Differs from Skia by about 0.0004.
3. **Simulator build and screenshot.** Look at the picture at 3x on several crops: outlines, thin features (door grooves, ring,
   bridge joints), flowers, edges between similar-brightness colours. Map device to design space with aspect-fill:
   `scale = max(viewW / W, viewH / H)`, design `x = (devX - (viewW - W * scale) / 2) / scale`.
4. **Full harness** for quality beyond SSIM (`tools/forest-regrade/scripts/`, build with `relocate.sh`): exact Python model of
   the iOS render (matches iOS to about 0.4/255, max 6/255), SSIM on luma (sigma 1.5), CIEDE2000 raw and low-passed, a
   per-region table (meadow, hedge, path, trees, bushes, bridge, door, stones, fox, flowers), heat maps, and edge sharpness as
   an erf-fitted sigma. Needs `potrace` (`brew install potrace`), Xcode with an iOS 18 simulator; the simulator UDID is
   hard-coded in `build_host.sh` and `render.sh`.

Simulator render hosts must be linked with `-Xlinker -platform_version -Xlinker ios-simulator -Xlinker 18.0 -Xlinker 18.5`,
or the UI is upscaled about 3% and every score is wrong.

**Benchmarks (forest, real renders, SSIM luma / mean dE00):**

| Version | SSIM | dE00 | Size / time |
|---|---|---|---|
| Stage 1, 5k regions | 0.9781 | n/a | 69k segs, 2.1 MB |
| **Stage 1, 10k regions (default)** | **0.9822** (MAE 1.7/1.7/1.8) | n/a | 110k segs, 3.4 MB; parse 25 ms release, 150 ms debug; draw 65 ms |
| Stage 1, 20k regions | 0.9860 | n/a | 182k segs, 5.7 MB |
| Stage 1, 40k regions | 0.9884 | n/a | 304k segs, 9.7 MB |
| Phase A (regrade) | 0.9828 | 0.67 | |
| **Phase B (final)** | **0.9851** (3x: 0.9824) | **0.55** (p95 1.52) | 3,569 shapes, 2.9 MB; release first draw 51 ms, redraw 0.03 ms |

Type-check is 1 to 2 s at every size. Returns diminish steadily; there is no sharp knee. Stage 1 below 0.98 at 10k: raise regions to
20k before changing anything else.

## 5. Troubleshooting (symptom, cause, fix)

| Symptom | Cause | Fix |
|---|---|---|
| Sawtooth or crawling edges on some outlines in a large scene, only on iOS 18 | **[reported]** SwiftUI/RenderBox reverses antialiasing coverage (c to 1-c) along stretches of outlines; which stretches depends on global draw order; hits Canvas fills, clips, tiled images, `MeshGradient` and `withCGContext` alike; not fixable from the data | Draw one cached `CGImage` rasterised on the CPU. The implementation is in `ForestPathIllustration.swift` (`ForestPathArt.image(of:size:scale:)`, `rasterize`, `ShapeRaster`, `RowShader`; check current line numbers). Confirm with the simulator check first. |
| Type-check takes minutes | Path data as numeric array literals (20k segments: 113 s) | Strings. 0.5 s. This is the default format. |
| Soft-edged halos or blurred outlines between similar-brightness colours | Edges found from brightness only | Per-channel colour gradient (`softzones.py` does this) |
| Hairline gaps or seams | Adjacent shapes antialiased separately | Stacked masks (each region extends under later ones) plus a full-canvas background shape |
| Streaky banding inside shapes | 2-stop gradients too coarse | Soft pass (cheap) or Stage 3 mesh fills (better) |
| Scores far below benchmarks | Wrong simulator link flags, or comparing the Skia preview | Section 4 |
| Disk fills (ENOSPC) during large arrays | Swap | Keep arrays int16/float16, delete old 4x maps |
| Incremental Xcode builds 8 to 9 s slower with a 3 MB file | "Index while building" | Project setting, not a code problem |

## 6. Stage 3: refinement (optional; use when quality matters more than time)

Needs existing vector data in the line format as input. Order (`pb_run.sh SRC_DATA TAG` runs it):
`pb_regions.py` (cost-based merging, cubic Lab polynomial fits, tau 6, plus sliver dissolution) then `pb_bounds.py`
(hard/soft/smooth boundary classes) then cell sizes then `pb_refine.py` (4x sub-pixel labels; `PB_BAND=2 PB_SIGCOST=2.0
PB_SIGIND=1.5`) then `pb_trace.py` (stacked masks, potrace on SDF-smoothed masks at 8x; `PB_BLUR=0 PB_OPT=0.8 PB_SDF=1.5`) then
`pb_rims.py` (thin pale outlines) then trace again (`PB_RIMS=1`) then `pb_fit.py`.

- **Fills:** joint least-squares bilinear mesh gradients per region (`meshfit.py`, `pb_fit.py`): smoothness 0.003, cell 6 units for
  regions over 5,000 px, cap 96 per side, membrane rows for hidden vertices, continuity weight 4 across smooth boundaries.
  Data line: `*W H RRGGBB... <path>`, mesh spanning the path's bounding rect grown 1 unit. SwiftUI blur radius equals the Gaussian
  sigma, so no calibration is needed.
- **Thin features** (door grooves, ring, bridge joints, fox tail) broke when retraced. For those, keep the earlier shapes and
  refit only their fills (`pb_fitsub.py`). Dropping invisible shapes: `prune.py`. Flower and bush transplants ghosted: rejected.
- **Revising an existing screen** (new reference of the same art): `flow.py` and `register.py` (DIS optical flow, sigmas 12 to 3)
  then `warp.py`, then refit. The forest reference was displaced up to 49 px. Needs `opencv`.
- Constants in these scripts are forest-specific: `art.py` hard-codes `W, H = 937, 1678` and the 14 layer ids.

## 7. Dead ends (all measured; do not repeat)

- **Parametric flowers, pebbles and spots, stroked line work:** capped at SSIM about 0.94 even at 50k segments. Trace what is there.
- **Segment budgets chosen up front:** 2k segments gives SSIM 0.86; many hours went on budget tuning.
- **Blur:** a uniform blur above sigma 0.3 lowers SSIM; per-layer blur makes outlines look out of focus.
- **Merging smooth boundaries** lost pebbles and rims; soft-merge gave fuzzy pebbles; blurred thin regions gave unstable fits.
- **Bisecting the iOS renderer defect** only confirmed it is order-dependent. Do not investigate; use the CPU image fix.
- **Generic SIMD and min/max in the CPU renderer:** 4x slower in debug builds. Use scalar loops.
- **Polling loops** while jobs run. Start the job, check once.

## 8. Known gaps (be honest about these in reports)

- **Layer naming is image-specific.** `semantic.py` has hand-placed polygons for 937x1678; `masks.py` and the flower rules use
  forest colours. A new image needs its own, or a generic `layers.json` (not built).
- **Swift type names are fixed** (`ForestPathIllustration`, `ForestPathArt`) in `templates/ForestPathArt.swift.tmpl`.
- **Stage 3's pipeline is forest-wired** (`art.py` constants) and has never started from Stage 1 output.
- **The iOS 18 renderer defect is reported, not reproduced by me.** My checks of `324a66d` on the simulator showed no sawtooth in
  the crops I looked at.
- Phase B's weaknesses: flowers (SSIM 0.9530, lower than Phase A), bushes slightly lower, a small notch in the hedge.
- Real-device frame rate and first-draw time are unmeasured (Phase B estimate for iPhone 11: 50 to 100 ms; debug first draw about
  360 ms).
- Two Phase A displacement fields were not recovered (`field_A` is regenerable with `register.py`).
- Stage 1 has never been run on a second image. Settings may need tuning.

## 9. Planned: scrolling screens at the bottom of the homescreen (not built)

Same width for every screen so they stack unscaled; match colours along shared top and bottom edges (trace each screen with
the neighbour's edge rows as context, or trace one tall composite); one view per screen in a `ScrollView`, parsed once and
loaded lazily. If you use the CPU image renderer, a cached image is about 12 MB per screen at 3x (1179x2556x4 bytes), so cache
only visible screens.

## 10. Working rules for the agent

- Measure real renders (SwiftUI, then simulator), not previews. Look at crops, not only numbers.
- Report SSIM, MAE, dE00 and, where relevant, edge sharpness; say which gate each came from.
- Offer cheap options with an effort estimate before open-ended work; do not run side experiments the user did not ask for.
- Do not commit, push or change app files unless asked. Keep outputs in the repo, not in scratch folders: scratch is cleared.
- Save any new script into the repo as you write it.

## 11. Repo map

- `tools/image2swiftui/`: `pipeline.py` and its modules, `harness/` (SwiftUI render on the Mac), `templates/`, `requirements.txt`.
- `tools/forest-regrade/scripts/`: 74 scripts, `host/Host.swift` (simulator render host), `inputs/` (reference and data sets, 15 MB,
  do not commit), `relocate.sh` (rewrites the hard-coded scratch path; always use it), `MANIFEST.md`.
  Core scripts: `art.py`, `model.py`, `pbart.py`, `pbrender.py`, `score.py`, `quick.py`, `acuity.py`, `meshfit.py`, `pb_*.py`,
  `build_host.sh`, `render.sh`, `register.py`, `flow.py`, `warp.py`. The rest are probes and one-off experiments.
- Commits: `324a66d` (Stage 1 output), `16f964a` (Phase B).
