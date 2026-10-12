# forest-regrade/scripts: manifest

Recovered 2026-10-10 from the original session's scratch folder, which still existed (so nothing was replayed from a
transcript; every file is a byte copy). Method and results: `../PROCESS.md`. Nothing here was run except the
verification at the bottom.

## Layout
- `tools/` 74 Python/shell scripts. `host/Host.swift` simulator render host. `inputs/` reference image and data sets.
- `relocate.sh WORKDIR` builds a runnable working copy. **Always use it.** The scripts hard-code the old scratch path
  (`/tmp/work`), which `relocate.sh`
  rewrites to WORKDIR with `sed`. It also creates `WORKDIR/venv` from `requirements.txt`.
- Needs: python3, `potrace` (`brew install potrace`), Xcode with an iOS 18 simulator. The simulator UDID
  `C79B1642-6DE6-4BD5-9BE2-8F6C49BC0929` (iPhone 16 Pro) is hard-coded in `build_host.sh` and `render.sh`; change it for another machine.
  `requirements-phaseA.txt` (opencv-python) is only for `register.py` / `flow.py`.
- Working-copy layout the scripts expect: `WORKDIR/{tools,host,ref/ref.png,data/<TAG>,out/<TAG>,venv}`.

## inputs/
(`inputs/data/` is git-ignored: 13 MB of intermediate data sets kept only on the original machine. `inputs/ref/ref.png` is committed. `data/pb32` is reproducible from the committed Swift file with `extract.py`; `base`, `warpA`, `fitE` are not recoverable from git, so the Phase A/B re-runs need them restored.)
- `ref/ref.png`: the 937x1678 reference (identical to the staged asset `forest path illustration.png`).
- `data/base`: the pre-regrade vector data (the old art). `data/warpA`: base warped onto the reference (Phase A step 1,
  also the donor of original shapes for the Phase B transplants). `data/fitE`: Phase A result (also the label source for
  per-region scoring). `data/pb32`: the Phase B data in the repo (14 `<layer>.txt` files).
  Format: one shape per line, `RRGGBB <path>` flat, `RRGGBB RRGGBB x0 y0 x1 y1 <path>` gradient, `*W H RRGGBB... <path>` mesh.

## a. Scoring and measurement
- `art.py` data model: parse layer files, flatten Béziers, 16-row AA rasterizer (`rasterize`), `LAYERS`, `W,H`.
- `model.py` exact iOS render model on an extended grid (Phase A, includes the soft/blur pass). `comp.py`, `mrender.py`
  older compositors. `pbart.py` Phase B shapes (flat/mesh, `PShape`, `load`/`write`). `pbrender.py` Phase B model
  renderer (any scale/offset, streaming). `devmodel.py DATADIR OUT.png` model render at device framing 393x852@3x.
- `score.py TAG` (reads `out/TAG/ref1x.png` + `dev3x.png`; env `LABELS=<datadir>` picks the region source): SSIM
  (luma, sigma 1.5), CIEDE2000 raw and low-passed (sigma 2 at 1x, 3 at 3x), per-region table (meadow, hedge, path, trees,
  bushes, bridge, door, stones, fox, flowers), writes `out/TAG/heat.png`, `delp.npy`. Needs `ref/ref.png`.
- `quick.py DATADIR` score via the Python model. `acuity.py TAG...` edge-sharpness (erf-fit sigma) vs the reference.
- `invmap.py IOS.png MODEL.png` finds iOS-vs-model differences (found the AA reversal). `worst.py`, `worst2.py` worst
  tiles. `zoom.py`, `cmpbox.py`, `devcrops.py` crop sheets. `deliverB.py` the Phase B figures. `geom.py` alignment check.
- Defect investigation (not needed to reproduce results): `bisect_inv.py`, `inv.py`, `inv396.py`, `inv_cached.py`,
  `layrev.py`, `whichrev.py`, `probe*.py`, `scenes.py`, `testvar.sh`, `complayers.py`, `outl.py`, `wobble.py`, `subset.py`.

## b. Simulator host
- `host/Host.swift`: SwiftUI app; reads `RENDER_JOB`, renders with `ImageRenderer`. Jobs (one per line):
  `full W H SCALE OUT`, `layers W H SCALE OUTPREFIX`, `split ...`, `parse 1 1 1 x`, `timing W H SCALE N`,
  `cold W H SCALE x`, `subset W H SCALE OUT id,id,...`. `cold` calls `ForestPathArt.image(of:)`, so it only compiles
  against the CPU-renderer version of `ForestPathIllustration.swift` (drop that line for older versions).
- `build_host.sh dev|repo`: swiftc build with `-target arm64-apple-ios18.0-simulator -Xlinker -platform_version
  -Xlinker ios-simulator -Xlinker 18.0 -Xlinker 18.5` (without the flags the UI is upscaled ~3%), installs
  `com.scratch.forestrender[.repo]`. `repo` compiles the repo's `ForestPathIllustration.swift`; `dev` uses `ART_SRC`
  (default repo file) with data loaded at runtime from `ART_DATA_DIR` via `mkdev.py`. `build_host_onone.sh` = `-Onone`.
- `render.sh dev|repo JOBFILE [DATADIR]` runs a job on the simulator (`SIMCTL_CHILD_RENDER_JOB`, `..._ART_DATA_DIR`).
  `rs.sh TAG DATADIR` renders 1x + 3x and scores. Uninstall hosts when done (`xcrun simctl uninstall`).
- `extract.py` splits a Swift file into code and per-layer data; `gen_swift.py SWIFT DATADIR OUT` writes a data dir into
  the Swift file's string literals.

## c. Mesh-gradient fitter
- `meshfit.py` (basis + LSQ with second differences). `fit.py`/`fit2.py` Phase A fills through the exact model
  (`fit2` lam_rel 0.05). `pb_fit.py BASE SHAPES.json DST` Phase B joint fit: lam_s 0.003, membrane rows for hidden
  vertices (0.5x between hidden pairs, 0.1x hidden-visible), mu 4 continuity across smooth/soft boundaries
  (`PB_CONT_SOFT=1`), ridge, cell 6 for regions > 5000 px, mesh cap 96. `pb_fitsub.py SRC DONOR LAYER CELL DST` refit a
  layer from donor geometry over fixed rest (`DONOR=-` and `LAYER=idx,idx` refits listed shapes; env `PB_LAM_M` adds a
  first-difference penalty). `prune.py SRC DST` drops hidden shapes (keeps shape 0). `pb_base.py` meadow base mesh.

## d. Phase B region and trace pipeline
Order: `pb_regions.py` (regions at 1x, merging + slivers via `merge.py`, `slivers.py`, `regions.py`) -> `pb_bounds.py`
(hard/soft/smooth classes) -> cell sizes (`pb_merge_smooth.choose_cells`) -> `pb_refine.py` (4x sub-pixel labels; env
`PB_BAND=2 PB_SIGCOST=2.0 PB_SIGIND=1.5`) -> `pb_trace.py` (stacked masks + potrace via `trace.py`; env `PB_BLUR=0
PB_OPT=0.8`, `PB_SDF=1.5` for SDF smoothing) -> `pb_rims.py` -> second trace (`PB_RIMS=1 PB_SDF=1.5`) -> `pb_fit.py`.
`pb_tail.sh TAG` runs everything after the 1x region map; `pb_run.sh SRC TAG` / `pb_all.sh` run it all (older settings).
`pb_smooth.py` outline smoother (prototype, not in the final data). `pb_soft.py`, `pb_softmerge.py` soft/blur paths
(abandoned). `pathio.py` writes paths back to the data format. Output dirs: `out/B/TAG_*`, `data/TAG`.

## e. Phase A registration and warp
`flow.py` DIS optical flow on edge structure, `register.py` iterative confidence-weighted refinement (sigmas 12..3,
writes `out/field_A.npy`; needs opencv). `warp.py` warps data by the field (border snapping) -> `warpA`. `softzones.py`
soft zones (tau 2). `patch.py`, `patch2.py` re-segment/retrace mismatch areas and border bands (run twice), then a residual
warp and `fit2.py` -> `fitE`. `showreg.py` registration plots.

## Swift CPU renderer (not copied)
In `ios/mockjuice/Views/Components/ForestPathIllustration.swift`: `ForestPathArt.Fill`/`RGB` (lines 45-58),
`image(of:size:scale:)` (65) with its cache `rasters` (74), `rasterize` (80), `ShapeDataReader` (144),
`ShapeRaster` (274), `RowShader` (374). Layer data starts at line 459.

## Verification (2026-10-10)
`relocate.sh /tmp/fr_verify`, `build_host.sh repo`, render `full 937 1678 1` and `full 393 852 3`, then
`LABELS=data/fitE score.py verify`: 1x SSIM 0.9851, dE00 0.55 (p95 1.52, low-passed 0.16); 3x SSIM 0.9824. Matches
PROCESS.md exactly. (Per region: flowers 0.9530, bridge 0.9783, door 0.9717.)

## Not recovered
- `out/field_A.npy` and `out/field_res3.npy` (Phase A displacement fields, ~12 MB each). Deleted during this session's
  cleanup. `field_A` is regenerable with `register.py` (deterministic). `field_res3` (residual warp after the first
  patch pass) has no single recorded command; its effect is already in `data/fitE`.
- The Phase A Swift file and intermediate datasets (`data/pb9`..`pb31`, `out/B/*`, `data/sz2`): not needed to reproduce
  Phase B (rebuildable by the pipeline from `inputs/data/fitE`), deleted or left in scratch.
- `PROGRESS_session.md`: the session's own working notes, kept as is.
