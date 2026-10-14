# forest-art: tools for the home-screen forest illustration

## Which art is live
`ios/mockjuice/Views/Components/ForestPathIllustration.swift`: **17 layers** (meadow, hedge, pathEdges, path, pond,
backTrees, pines, bridge, bushes, doorBush, door, stones, rocks, fox, log, flowers, frontTrees), about 2,133 shapes,
with a pond, rocks and a log. The door, stones and fox layers exist but are empty. Always read and count from the live
file. An older 14-layer version (3,569 shapes, with fox and door, no pond) is outdated; it exists only in git history
(commit `1a3c35a`, "Phase B quality pass").

## What is here
Only tools for previewing and checking art written in the Swift file's shape format. The tools that traced a reference
image into shapes were removed; they remain in git history (`tools/forest-art/`, `tools/forest-regrade/`,
`tools/forest-v2/`, `tools/image2swiftui/`, and the 43 KB version of this README).

| File | Purpose |
|---|---|
| `scripts/relocate.sh WORKDIR` | builds a runnable working copy (the scripts hard-code a scratch path that it rewrites) |
| `scripts/tools/extract.py SWIFT OUT_DIR` | splits the Swift file into one data file per layer (empty layers give empty files) |
| `scripts/tools/art.py`, `pbart.py`, `pbrender.py` | Python copy of the iOS renderer (accurate to about 0.4/255): `pbrender.py DATA_DIR OUT.png [SCALE]` |
| `scripts/tools/score.py`, `acuity.py`, `rs.sh` | similarity and edge-sharpness scoring against a reference image |
| `scripts/host/Host.swift`, `scripts/tools/build_host.sh`, `render.sh`, `mkdev.py`, `devmodel.py` | simulator render host: renders the art through SwiftUI on the iOS Simulator (needs Xcode with an iOS 18 simulator; UDID hard-coded) |
| `scripts/inputs/ref/ref.png` | reference image of the older art (scoring input) |

## Data format (one shape per line, back to front per layer)
`RRGGBB <path>` flat; `RRGGBB RRGGBB x0 y0 x1 y1 <path>` gradient; `*W H RRGGBB... <path>` bilinear mesh spanning the
path's bounding rect grown by 1 unit. Paths use M, L, C, Z and relative l, c. Design space 937x1678. The CPU renderer
in the Swift file (not SwiftUI path drawing) produces the pixels, because SwiftUI reverses antialiasing on iOS 18.
Observed mesh rule in the live art: flat under about 10 u², 2x2 under about 100 u², about 4 u cells above that.
