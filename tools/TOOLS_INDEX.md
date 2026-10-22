# Image-to-SwiftUI tools: index

Restored from git history (`0505445^`) for converting new illustrations into the app's layered vector format. Nothing here
has been re-run since restoring; imports resolve and every script parses. Read `SWIFTUI_RECONSTRUCTION.md` first.

## Two routes

| Route | Entry point | Evidence in the docs |
|---|---|---|
| One command: image to Swift data | `image2swiftui/pipeline.py IMAGE --out OUT.swift --regions N` | 10k regions SSIM 0.9822 in about 80 s; 40k regions 0.9884 (9.7 MB) |
| Refinement chain from a per-pixel layer map | `forest-art/notes/v2-README.md` (run order) | edge fit +0.005, 4 px mesh cells 0.987, 3 px cells 0.989 (6.9 MB); about 45 min compute per image |

## Where things are

- `image2swiftui/`: trace pipeline, Swift template (`templates/`), simulator harness (`harness/`). Needs `skia-python`.
- `forest-art/scripts/tools/`: scoring (`score.py`, `acuity.py`), the Python copy of the iOS renderer (`art.py`, `pbart.py`,
  `pbrender.py`), the v2 and `pb_*` refinement chain, seam tools (`v2_extend.py`, `v2_composite.py`, `v2_gap.py`).
  `forest-art/scripts/relocate.sh WORKDIR` builds a runnable working copy (the scripts hard-code `/tmp/work`).
  Needs `opencv-python-headless` for `register.py` and `flow.py`.
- `forest-art/notes/`: v2 run order, seam notes (`v2-PAUSED-seam-notes.md`), regrade process and script manifest.

## Wired to the old forest image (adapt, do not reuse as-is)

- Layer groups and polygons: `image2swiftui/semantic.py`, `image2swiftui/hf_groups.py` (14 layers),
  `forest-art/scripts/tools/v2_layermap.py` (17 layers with hand-placed object polygons).
- `image2swiftui/masks.py`: colour thresholds for the cream path and brown borders.
- `forest-art/scripts/tools/v2_gen_swift.py`: the 17 layer names and docs. Its first argument is a Swift file that supplies the
  renderer code; use the live `ios/mockjuice/Views/Components/ForestPathIllustration.swift` (the original template backup was
  not restored).
- Swift type names in `image2swiftui/templates/ForestPathArt.swift.tmpl`; the 937x1678 canvas in `pipeline.py`.
- Simulator UDID in `build_host.sh` and `render.sh`.

## Not restored (no value for new images)

Phase A colour-regrade tools (they map one old reference onto another), old art outputs and backups, the old reference
image, probes and diagnostics for that regrade, `forest-regrade/scripts/PROGRESS_session.md`, `tools/mascot/`.
