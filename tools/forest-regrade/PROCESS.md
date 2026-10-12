# Forest path illustration: colour regrade (Phase A) and quality pass (Phase B)

Done 2026-10-09. Result committed as `16f964a` (`ForestPathIllustration.swift`).
The scripts named below were in a session scratch folder (`/tmp/work/tools`) and are
NOT in the repo. This document is the method; `tools/image2swiftui/` documents the earlier original trace, not this work.

## The brief
- Re-grade the pure-SwiftUI home illustration 1:1 to a new reference PNG (937x1678), then (Phase B) make it
  native-4K crisp: accurate edges, real gradients instead of blur-faked shading, no halos or fake detail.
- Keep `ForestPathLayers([ids])` and the 14 layer IDs: meadow, hedge, pathEdges, path, backTrees, pines, bridge,
  bushes, doorBush, door, stones, fox, flowers, frontTrees.
- Pure SwiftUI, no third-party libraries, iOS 18.0 target, 60 fps on iPhone 11+, avoid path boolean ops.
- Measure everything on the iOS simulator (393x852 @3x via ImageRenderer). Report SSIM and CIEDE2000 globally and per
  region with heat maps. Stop after each phase for approval.

## Measurement setup (built first)
1. A throwaway swiftc host app on the simulator renders the art through `ImageRenderer` from job files
   (`full`, `layers`, `split`, `parse`, `timing`, `cold`). Link flags `-Xlinker -platform_version -Xlinker ios-simulator
   -Xlinker 18.0 -Xlinker 18.5` are required or the UI is upscaled ~3%.
2. An exact Python model of the iOS render (AA coverage from 16 subsample rows, source-over stacking) matched iOS to
   ~0.4/255. Everything was fitted against this model and then verified on the simulator.
3. Scoring: SSIM on luma (sigma 1.5); CIEDE2000 raw and low-passed; per-layer region masks (meadow, hedge, path, trees,
   bushes, bridge, door, stones, fox, flowers); heat maps; edge sharpness as the erf-fitted edge-spread sigma.
4. Baseline: SSIM 0.686, mean dE00 15.8.

## Phase A: regrade (approved)
- The reference is the same drawing as the old vector art, displaced non-rigidly (median 25 px up, max 49).
  Registration: DIS optical flow on edge features, refined iteratively with confidence-weighted smoothing.
- Warp the vector control points by the displacement field (snap borders), retrace the bottom strip that had no source.
- Joint least-squares refit of every shape's colours and 2-stop gradients through the exact model, including the old
  blurred "soft pass" (SwiftUI blur radius == Gaussian sigma). Residual-spot patches, a second residual warp, refit.
- Result on iOS: 1x SSIM 0.9828, dE00 0.67, low-passed 0.33; device 3x SSIM 0.9810; redraw 7 ms.
- Found: reference grain is only 0.66/255, not reproduced.

## Phase B: quality pass
Region pipeline (outlines rebuilt from a 4x upscale, no blur anywhere):
1. Cost-based region merging (cubic Lab polynomial fits), sliver dissolution, boundary classes (hard/soft/smooth).
2. 4x sub-pixel label refinement against the bicubic-upsampled reference (band 2 px), minimum-width opening, bead
   dissolution.
3. Stacked masks (each region extends under later ones), potrace on SDF-smoothed masks at 8x (tolerance 0.8).
4. Rim bands for thin pale outlines; a membrane-fitted base mesh under the meadow (fills antialiasing gaps).
5. Fills: joint least-squares bilinear mesh gradients per region (cells 6 units for large regions, cap 96 per side),
   with second-difference smoothness, membrane rows for hidden vertices, continuity across soft/smooth boundaries.
6. No blur: shadow edges measure as sharp as hard edges (sigma ~0.6-1.0 px at 1x).

Data format (in `ForestPathIllustration.swift`): one shape per line, `RRGGBB <path>` flat,
`RRGGBB RRGGBB x0 y0 x1 y1 <path>` 2-stop gradient, `*W H RRGGBB... <path>` bilinear mesh spanning the path's bounding
rect grown by 1 unit.

### The renderer problem (important)
SwiftUI/RenderBox path rasterisation on iOS 18.2 reverses antialiasing coverage (c -> 1-c) along parts of some outlines
in large scenes, giving sawtooth edges. Deterministic, depends on global draw order, hits Canvas fills, clips, tiled
images, MeshGradient, withCGContext, drawingGroup and layers alike. Not fixable from the data.
Fix: draw one cached CGImage. `ForestPathArt.image(of:size:scale:)` rasterises on the CPU (Core Graphics 8-bit coverage
per shape, Swift compositing of flat / gradient / mesh fills, 16 parallel row bands, cropped to the subset's pixel
bounds, cached per layer subset). Use scalar loops: generic SIMD and min/max are 4x slower in -Onone builds.

### Hybrid data (final = "pb32")
Traced shapes broke thin features (door grooves, ring, bridge highlight, fox tail speck). For door, stones, fox and
bridge the original vector shapes (aligned in Phase A) were put back and their mesh fills refitted over the fixed
rest; invisible shapes pruned (base kept); 33 wild 2-wide meshes refitted with a first-difference penalty.
Flowers and bushes were also tried and rejected (ghosting).

## Final results (simulator)
- 1x SSIM 0.9851, dE00 0.55, low-passed 0.16; device 3x SSIM 0.9824; edge sigma 0.531 px (Phase A 0.581, reference
  bicubic 0.658).
- Release: parse 8 ms + raster 33 ms (first draw 51 ms), redraw 0.03 ms. Debug (-Onone): ~360 ms first draw.
- iOS == model (max 6/255); on-screen == ImageRenderer; 14 stacked layer views == single view (max 3/255).

## Known weaknesses and unverified
- Flowers (one purple notch, lumpy petals; SSIM 0.9530, worse than Phase A 0.9606), bushes slightly below Phase A,
  small notch in the hedge's pale strip.
- Real-device fps and first-draw time unmeasured (iPhone 11 estimate 50-100 ms).

## Dead ends (don't repeat)
Merging smooth boundaries lost pebbles/rims; soft-merge produced fuzzy pebbles; blurred thin regions gave unstable
fits; MeshGradient/clip/tiled-image all hit the AA reversal; dummy-draw probes and bisecting only confirmed it is
order-dependent; SIMD loops were slower.

## Lessons
The cheaper route was: keep the original aligned vector shapes, refit colours, draw once on the CPU. See the memory note
`cost-scoping`.
