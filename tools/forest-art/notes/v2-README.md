# forest-v2

Homescreen illustration rebuilt from the new reference
(`ios/mockjuice/Assets.xcassets/theforestpathillustration.imageset/the forest path illustration.png`).

- `backup/ForestPathIllustration.phaseB.swift`: the Phase B art this replaces.
- `ForestPathIllustration.v2.swift`: the new art (17 layers, CPU renderer unchanged). Not yet installed in the app.
- `scripts/`: every script written or changed for this pass. Copy them over a working copy made with
  `tools/forest-regrade/scripts/relocate.sh WORKDIR` (plus `pip install opencv-python-headless`); the reference goes to
  `WORKDIR/ref/ref.png`.

## Run order (from `WORKDIR/tools`, out/B tags)

    python v2_layermap.py ../out/layermap.npy ../out/layermap.png        # layer per pixel (17 layers, new object polygons)
    python v2_regions.py ../out/layermap.npy ../out/B/t12 12              # 1x region map from the image, tau 12
    python v2_halos.py ../out/B/t12 ../out/B/w12 6 3                      # merge haze rings, dissolve AA slivers
    python pb_bounds.py ../out/B/w12                                      # hard / soft / smooth boundaries
    zsh v2_tail.sh w12                                                    # cells, 4x labels, trace, fit
    V2_CLEAN=1 V2_RIMS=0 zsh v2_chain.sh w12 x4 48                        # 2 boundary-fit passes, 4 px mesh cells
    python v2_gen_swift.py ../../tools/forest-v2/backup/ForestPathIllustration.phaseB.swift ../data/x4 OUT.swift

Taller (phone-shaped) reference of the same scene: first

    python v2_extend.py NEW.png ../ref/ref.png ../out/layermap.npy ../ref/ref.png ../out/layermap.npy   # (keep copies of the old two)

then the run order above from `v2_regions.py` (skip `v2_layermap.py`), and pass the new size to `v2_gen_swift.py`
(`... OUT.swift 937 2037`). The canvas size follows `ref/ref.png` everywhere (`art.py`, `score.py`, `rs.sh`, `acuity.py`).

Verify: `LABELMAP=../out/layermap.npy zsh rs.sh TAG ../data/TAG dev`, `python acuity.py TAG`,
`python v2_acuity_why.py TAG ../out/B/TAG`, crops with `v2_sheet.py` / `v2_cmp.py`, gap analysis with `v2_gap.py`.

## What each new step is for (measured)

- `v2_edgefit.py`: moves 4x boundary sub-pixels where that lowers the 1x error against the reference (anti-aliased
  pixel model, length penalty). SSIM 0.979 -> 0.984. Geometry only.
- `v2_refit.sh` / `PB_NMAX`: 4 px mesh cells and a 240-node cap for large regions (the 96 cap made path and meadow
  cells ~10 px). SSIM 0.984 -> 0.987. 3 px cells give 0.989 at 6.9 MB of data.
- `PB_CONT_SOFT=0`: soft-edge boundaries crisp instead of joined by fill continuity. Slightly better scores.
- `v2_halos.py`: without it, the reference's glow rings and AA slivers become thin wobbly shapes at 6x.
- Dead ends: protecting thin regions in `pb_refine.py` (`PB_PROTECT`, makes broken rims), finer region maps (tau 6:
  no gain), trace settings (no gain), down-weighting edge pixels in the fit (`PB_EDGEW`, no sharpness gain).
- `v2_acuity_floor.py`: a perfect hard edge scores 0.508 px on `acuity.py`; the 0.55 gate cannot be met while the
  reference's soft painted transitions (18% of sampled edges) stay smooth gradients.
