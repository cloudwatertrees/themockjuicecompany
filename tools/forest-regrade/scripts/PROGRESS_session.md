# Forest path regrade — progress
Scratch: this dir. venv: ./venv (numpy scipy skimage cv2 pillow). Ref copy: ref/ref.png (937x1678).
Repo file: ios/mockjuice/Views/Components/ForestPathIllustration.swift (do not commit until approved).
Note: mockjuiceApp.swift has a pre-existing TEMP change (MascotAnimationPlayground) - not ours, leave it.

## Phase 0 — measurement setup
- [ ] sim host renderer (ImageRenderer, iPhone 16 Pro sim, -platform_version flag)
- [ ] score script (SSIM, dE00, per-region, heat map)
- [ ] baseline score of current vector
- [ ] geometry alignment check

## Phase A — colour grade (stop for approval)
## Phase B — quality (stop for approval)

### Phase 0 results (done)
- Host: tools/build_host.sh dev|repo, tools/render.sh dev JOB [DATADIR]. Jobs: full/flat/layers/maskprobe/blurprobe/timing.
- Python model (tools/art.py, comp.py) matches iOS flat render: mean 0.41/255.
- SwiftUI blur radius == Gaussian sigma in design units (2.47 px @1x for 2.5). Soft pass covers 66% of canvas.
- Baseline: 1x SSIM 0.686, dE00 15.8; dev3x SSIM 0.756, dE00 15.5.
- GEOMETRY: ref is displaced non-rigidly vs vector (median 25px up, max 49, top-left trees ~30px left);
  bottom 4-36px strip of ref has no vector source. Field from tools/register.py (sigmas 12..3) -> out/field_A.npy,
  residual tiles median 0.05 / p99 0.35 / max 0.8 px. field maps render pt x -> ref pt x+f(x) (pixel-index coords).
- Plan A: warp control points by field, retrace bottom strip, LSQ refit colours+gradients w/ exact render model, iterate.

### Phase A (DONE, awaiting approval) — data dir data/fitE, written to repo Swift file (uncommitted)
Pipeline: warp base geometry by field_A (tools/warp.py, border snapping) -> soft zones regenerated from ref
(tools/softzones.py tau=2 -> data/sz2) -> fit2 (exact extended-grid iOS model, tools/model.py; lam_rel 0.05)
-> patch2 (border bands + residual spots, Felzenszwalb+potrace 4x) x2 -> residual warp (field_res3) -> fit2.
iOS fitE: 1x SSIM 0.9828, dE00 0.67 (p95 1.71), lowpass 0.33 (p95 0.71); dev3x SSIM 0.9810 dE00 0.69.
Repo-compiled host == dev render (max diff 0). App builds. Timing ImageRenderer 393x852@3x: 6.41 -> 6.99 ms.
Grain sigma 0.66/255 in flat areas (not reproduced; invisible). Deliverables: deliver/phaseA_*.png
Original Swift file backup: ForestPathIllustration.orig.swift (scratch).

## Phase B (in progress) — approved Phase A 2026-10-09
Findings: ref edge sigma @1x 0.48px (sharp); bicubic@3x 0.66 dev px; Phase A strong edges 0.58 (tools/acuity.py).
Phase A's soft look = lumpy/wobbly traced outlines, slivers, blotchy shading (see out/zoomA*.png).
MeshGradient in Canvas .style(): maps to Path.boundingRect (TIGHT curve bounds); smoothsColors=false => exact bilinear
in sRGB; smoothsColors=true => smoothstep basis (zero tangents => ripples) -> use bilinear. 1000 4x4 meshes ~1ms.
Fill residual (Lab RMS): bilinear mesh cell 16-24u ~0.6-1.1 for mid/large regions (cubic poly level).
Plan: regions (merge.py cost-based deg3 tau6 + slivers.py) -> boundary classes -> 4x subpixel refine -> stacked
masks + potrace -> joint LSQ mesh fills (no global blur; blur only for soft-edged regions) -> new Swift format.
Phase B progress (2026-10-09):
- Swift renderer changed (uncommitted): soft pass + softZoneData removed; mesh lines '*W H colours path' -> bilinear
  MeshGradient drawn as clip(path)+fill(boundingRect inset -1) (direct mesh fill corrupts neighbours' AA on iOS 18).
- Pipeline: tools/pb_all.sh SRC TAG (pb_regions -> pb_bounds -> cells -> pb_refine [cost smoothing, min_width,
  dissolve_beads] -> pb_trace -> pb_fit). Python model: pbart.py/pbrender.py (matches iOS ~172px>12).
- Best so far: data/pb13 = pb9 geometry (beads dissolved max_len 10/width 2), lam_s 0.003, cell 6 for regions >5k px,
  mesh cap 96. Model: SSIM .9857 dE .537 lp .155(p95 .37); iOS 1x SSIM .9831 lp .174 (dither noise). 2.28MB, 3.3ms.
- Open: light rims (1px pale outlines) removed with beads; some outline lumps (fox, leaf, bridge arch top).
- (later) iOS 18 bug: MeshGradient (even clip+rect) in Canvas inverts AA coverage of other fills in some scene
  configs (sawtooth edges). FIX: mesh lines rendered as WxH CGImage (vertex colours, sRGB) drawn .interpolation(.low)
  into rect with pixel centres on vertices, clipped to path. Matches model (mean .071/255), 1.73 ms/render.
- Current best: data/pb19 (geometry out/B/pb18 + PB_SDF=1.5 SDF-smoothed 8x tracing; rims; membrane reg; lam .003;
  cell 6 >5k px; nmax 96). iOS 1x SSIM .9846 dE .561 lp .170. Pipeline: tools/pb_run.sh (+ retrace with PB_SDF).
- Disk: swap filled the disk once (ENOSPC). Keep big arrays int16/float16; delete old out/B/* 4x maps.
STOPPED (usage limit) 2026-10-09: repo restored to approved Phase A (fitE + soft pass). Phase B WIP renderer saved as
ForestPathIllustration.phaseB_wip.swift (scratch). Open: image-mesh+clip still serrates some edges on iOS (flat-only
scene is clean) -> test .tiledImage fill (host job 'imgvar tiled'); soft shadow edges render crisp; rims weak.
- (resume 2026-10-09) tiledImage mesh fills (one px per vertex, .interpolation(.low), path in bitmap px space +
  concatenated transform) replaced clip-based mesh; repo holds pb21 (2385 shapes, SSIM .9840-ish, 1.56 ms, parse 32 ms).
- pb22 = pb18 regions, PB_BAND=2 refine, SDF trace, rims, base mesh: iOS 1x SSIM .9840 dE .567 lp .173; 1.70 ms.
- pb22 iOS shows reversed AA coverage (c -> 1-c) along the big brown pathEdges mesh (#396) edges: 408 px > 40 vs model,
  nowhere else (tools/invmap.py). #396 alone renders right; scene-context dependent (iOS renderer bug). pb21 clean.
  Bisecting the trigger (tools/bisect_inv.py); variants var/nz.swift (nonzero fill), var/layer.swift (drawLayer/layer).
### Phase B (DONE, awaiting approval) — 2026-10-09
- Root cause of sawtooth: SwiftUI/RenderBox path rasterisation (iOS 18.2 sim) reverses AA coverage (c -> 1-c) on
  stretches of outlines; position set by global draw order (dummy draws shift/clear it). Hits Canvas fills, clips,
  tiled images, MeshGradient and withCGContext alike; pb21 (old repo state) had it too. Not fixable from data.
- Fix (repo): ForestPathLayers draws a cached CGImage. ForestPathArt.image(of:size:scale:) rasterises on the CPU:
  Core Graphics 8-bit coverage per shape + Swift compositing of flat / 2-stop / bilinear mesh fills, 16 row bands
  in parallel, cropped to the subset's pixel bounds, cached per layer subset (latest size). Layer API unchanged.
  iOS == model (max 6/255); on-screen == ImageRenderer (max 0); 14 stacked views == single (max 3/255).
- Data pb32 = pb22 + original vector shapes (data/warpA) for door, stones, fox, bridge refit with meshes over fixed
  rest (tools/pb_fitsub.py), hidden shapes pruned (tools/prune.py, base kept), 33 wild 2-wide meshes refit with
  first-difference penalty. Flowers/bushes transplants rejected (ghosting).
- Final: 1x SSIM .9851 dE .55 lp .16; dev3x SSIM .9824 lp .17; edge sigma 0.531 px (A .581, ref bicubic .658).
  Release cold: parse 8 ms + raster 33 ms (first render 51 ms), redraw 0.03 ms (A: 7.5 ms every redraw).
  Debug (-Onone): parse 248 ms + raster 94 ms. Repo file 2.86 MB, 3569 shapes. Hosts uninstalled.
- Deliverables: deliver/phaseB_{full.jpg,heat.png,crops1-4.png,renderer_defect.png}.
- Known: flowers (one purple notch, lumpy petals; SSIM .9530 < A .9606), bushes SSIM .9758 < A .9782, small hedge
  notch. Real-device timing/fps unverified.
