# image2swiftui

Process, measured results and dead ends: [../SWIFTUI_RECONSTRUCTION.md](../SWIFTUI_RECONSTRUCTION.md).

Turns a flat-colour illustration into a layered, pure-SwiftUI vector file. Recovered from the session that produced
`ForestPathIllustration.swift` (commit `324a66d`: ~10k traced shapes, 14 named layers, SSIM 0.9822 crisp / 0.9830 with the
soft-shading mask). Running it on the original reference reproduces that file.

## Run

    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/python pipeline.py art.png --out ForestPathIllustration.swift --regions 10000
    harness/render.sh ForestPathIllustration.swift render.png      # real SwiftUI render
    .venv/bin/python score.py art.png render.png                   # SSIM / MAE

About 5 minutes for 10k regions on 8 cores.

## Pipeline

| Step | File | What it does |
|---|---|---|
| over-segment | `pipeline.py` | Felzenszwalb, about 93k fine regions |
| name layers | `semantic.py`, `masks.py`, `hf_groups.py` | colour class x hand-placed ROI polygons -> 14 layers |
| merge | `regions.py`, `dendro.py` | cheapest same-layer merges (affine colour-model error) down to N regions |
| re-place boundaries | `superres.py` | 4x sub-pixel boundaries against the reference |
| trace | `hf_vec.py`, `bezier.py` | occlusion-aware outlines to cubic Beziers; flat or 2-stop gradient fills |
| soft zones | `softzones.py` | canvas minus a band around every hard colour edge |
| write Swift | `emit_swift.py`, `templates/` | layers as SVG path-data strings in multi-line literals |

## Limits

- `semantic.py` ROI polygons and layer names are specific to the 937x1678 forest image. A new image needs its own.
- The Swift template names (`ForestPathIllustration`, `ForestPathArt`) are fixed.
- Does not include the later "Phase B" rework in the repo (mesh gradient fills, CPU rendering).
