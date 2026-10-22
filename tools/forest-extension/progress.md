# Forest extension — progress

Checksum (facts.json sha256 of ForestPathIllustration.swift): `275282563bc90e5cf4439b706be591437f3fcc130d6b788ced241d26b0f04aa3`

## State: run 3 — complete; waiting for final visual approval (nothing committed)
Brief v2 order: 1 in-context harness -> 2 shared irregularity layer (flowers, pine) [CHECKPOINT] -> 3 bush, rock, tree
shading -> 4 ferns, old tree, stream [CHECKPOINT] -> 5 assembly + Swift + join tests + simulator [CHECKPOINT].

## Step 1-2 results (2026-10-16)
- `scripts/incontext.py NAME [seed] [scale]`: removes the live element (pick predicate), fills the hole with a ground
  underlay (only where no kept object covers it; colour = normalised-convolution fill from surrounding ground-like
  pixels), inserts the recipe in its true layer position, renders live | new at the same crop. Elements: flowers,
  pine, bush, rock, tree. Exposes `ctx.ground_field` for shadow shapes.
- `scripts/measure_irregularity.py` -> `irregularity.json` (live): mottling residual lum std ~4-6 /255, corr ~8 u
  (dark tones stronger); 1 u turning p90 22-33 deg; lobe-length CV 0.5-0.73; ground darker by ~30-39 lum next to
  foliage, ~13-18 at 25-40 u below objects. Caveat: outline stats are biased by the live mosaic's many tiny shapes.
- `scripts/irr_compare.py` sanity table (crops/step2/sanity_table.txt).
- `scripts/fx/irregular.py`: organic() = wobble (position-based normal displacement fine/mid/coarse) + mottle (tone-
  weighted value noise ~8 u + hue drift) + live mesh rule; inset(), vary() (lognormal CV), shadow() (separate soft
  ground shape darkened from a ground field).
- Flowers: rebuilt with spoon petals (narrow base, round tip; fullness per kind), lognormal petal sizes, off-centre
  disc, organic(). In context: close to live.
- Pine: tone-region restructuring failed over 4 rounds (regions read as decals/dots) -> reverted to Stage-1 geometry
  + organic() + asymmetry + halo with painted-in shadow + sharper notches (k 0.4). Structure gap remains (lower-tier
  leaflets too long/horizontal, tiers merge, seed-dependent odd top leaflets).

## Run 3 (autonomous, approved 2026-10-17): specimen recombination
Approved: drop `private` on ShapeRaster/ShapeDataReader. Only planned stop: final shuffled comparison.

### Construction guide (read from live pieces)
- **Bush** (bush_bridge 73 obj/46 ground): ~70 leaf pieces, each a whole palmate leaf with its own mesh; back leaves
  darker (`426F55`-`598A60`), front/lit leaves lighter; a pale halo + under-bush olive ground pieces in `meadow`; flowers
  sit on pale petal-backing pieces painted into `bushes`/`meadow` (no leaves under them).
- **Rock**: base silhouette in `rocks`, but the light top face is painted in `meadow`/`bushes`; facets are separate
  pieces sharing the silhouette edge on one side; ferns in front belong to the group (hidden faces are unpainted).
- **Bell trees**: not tier+overlay. Each tree is interlocking regions: light half-bell lit pieces (whole tier on the lit
  side, sharing the outer edge), dark under-hem bands, darker body; neighbouring trees interlock, so single trees
  cannot be isolated; groups are cut straight where they touch the canvas edge.
- **Pine**: one body mesh per tier, light tip pieces, pale egg halo; flowers in front.
- Draw order inside a group spans layers (meadow < bushes < rocks ...): place groups with all object pieces merged into
  one target layer in source order; ground (meadow-coloured, meadow-layer) pieces re-grounded and drawn first.

### Method + lessons
- `fx/specimen.py`: Specimen (centre-in-box selection, all layers, ground/object classification by colour vs the
  estimated live ground), place() (affine: mirror to the new light side, scale, rotate; recolour; wobble; ground
  pieces = new ground x live ratio; merge layer). `fx/composites.py`: bush (leaves from a source, own flowers
  replaced by generated flowers at the transformed flower centres, petal backings painted shade green), generic, rock.
- Lessons: (1) layer-based selection misses pieces (rock top face lives in meadow) -> select by region, merge layers.
  (2) whole specimens at scale 1 = copies -> always mirror/rescale/recolour and swap flowers. (3) yellow-green leaves
  look like ground to a colour test -> only meadow-layer pieces or pieces equal to the local ground are ground.
  (4) partially occluded live pieces look wrong alone -> place whole groups with their occluders. (5) tiers cannot be
  restacked (method abandoned after 1 round); trees placed as edge-anchored groups (cuts stay on canvas edges):
  trees_ml (clean), trees_bl / trees_br (bottom cut -> at the extension bottom or behind a shrub row).
- In context: bush (bush_bridge, bush_rightbridge sources) and rock (rock_big x0.9, rock_seam x1.9 mirrored) pass.

### Assembly + Swift (2026-10-17)
- Pine: pine_top / pine_low specimens with flowers swapped (`composites.pine`). Ferns: fern_rockleft, tuft_a, tuft_b,
  bush_rightbridge (`composites.fern`). Pond parts: lily, pad, reeds specimens. Rocks in water: stone_pond.
- Old tree: `fx/oldtree.py` bespoke (3 rounds): flared trunk + 5 capsule roots (short on the path side), lit copies
  (base shifted toward the light, clipped), under-canopy shade, moss; canopy = rim lobes + cloud lobes each with a lit
  copy and highlight; soft shadow.
- Stream: `fx/water.py` (bank strip, depth-shaded water mesh, light rim band inside the far edge, ripple dashes).
- `scene.build()` full composition (bands A/B/C); `generic_caps()` closes every live object shape cut by the seam
  with shallow tangent-blended caps; edge tree groups anchored with exact scale so cuts land in the bleed.
- ForestPathIllustration.swift: `private` dropped on ShapeDataReader/ShapeRaster (approved). File sha changed to
  873089dc...; data section unchanged: data_sha256 b84e269f... (facts.json; require_facts now guards data_sha256).
- `scripts/emit_swift.py` -> ForestPathExtension.swift (5.3 MB, 2455 shapes): ForestPathExtensionArt (nonisolated,
  parse via ShapeDataReader, rasterize(size:scale:) via ShapeRaster, seamGround/topBounce/bottomBounce colours).
- HomeSceneView: ScrollView + VStack(live, extension), HomeSceneLayout (s rule, pixel-rounded segment height, resting
  offset), ForestPathExtensionView (detached raster task, own cache, seamGround fallback), bounce background.
- Build: the sandbox blocks CoreSimulator (simdiskimaged) and DerivedData writes for Bash xcodebuild; building via the
  simulator build tool (generic destination) instead.

### Verification (2026-10-17)
- Build: the exact brief command succeeds when run from the Terminal panel (Bash sandbox blocks CoreSimulator).
  Log: `build_last.log`.
- Numeric join (`scripts/jointest.py` -> `jointest.json`): 393x852, 402x874, 820x1180 at 1/2/3x; no step in the
  row-mean metric; per-24px-bin metric flags only 820x1180@3 at x~55 u (+0.5 over threshold): fern-mound cap corner,
  ~2 px at phone scale, accepted.
- Simulator (iPhone 16 Pro): resting screen identical to before; join mid-screen shows no step; bottom bounce colour
  matches the ground; extension rendered from the detached task.
- Final blind comparison: `scripts/final_compare.py` -> `crops/final/*.png`, key `final_compare_KEY.json`.
- Perf host: `perf/build_run.sh` (PerfHost.swift, -O) -> `perf/perf_last.log`.
- Fixes during assembly: tree groups exclude flower/pale/grey pieces (NOFLOWER), bush specimens exclude stone
  pieces (notstone), pine moved clear of the left tree group.

### Next (if the user requests changes)
- Regenerate: `python scene.py` via `fullview.py rebuild`, then `emit_swift.py`, `jointest.py`, `final_compare.py`,
  build from Terminal.

## Environment
- Python venv: `zsh tools/forest-art/scripts/relocate.sh <scratch>/w`; if pip fails with SSLCertVerificationError
  (sandbox), run `<scratch>/w/venv/bin/pip install --use-deprecated=legacy-certs -r tools/forest-art/scripts/requirements.txt`.
- Run scripts from `tools/forest-extension/scripts/` with that venv's python. They import the repo copy of the
  forest-art renderer (common.py). Scratch output dir = `$FX_SCRATCH` (default: the first session's scratchpad `/fx`;
  set FX_SCRATCH in a new session).

## Files
- `facts.json` (stage0_facts.py), `seam.json` (stage1_seam.py), `style_spec.md`, `recipes.json`, `crops/stage1/*.png`.
- `scripts/common.py` paths, live loader, render/save, `require_facts()` (stops on checksum change).
- `scripts/view.py OUT x0,y0,x1,y1 SCALE [layers=..] [ids] [alone] [src=live|ext|both]` crop / ID-colour viewer.
- `scripts/proto.py NAME [seed]` original crop beside recipe output (tree, pine, bush, rock).
- `scripts/seamview.py OUT [x0,x1] [above] [below] [scale] [rebuild]` live bottom strip stacked on the extension top.
- `scripts/scene.py` extension composition (`build()`), currently: path + band + cobbles + pebbles + ground + pebble cap.
- `scripts/extdata.py` builds/caches extension data in `$FX_SCRATCH/ext_data`; `translate()`.
- `scripts/fx/`: geom (SDF, contours -> paths), paint (ramps, noise, emit per mesh rule), trees (bell_tree), plants
  (fern_pine, flower, palm_leaf, leaf_clump), stones (rock, pebble), pathgen (PathModel, PathEdges with seam blend),
  ground (paint Buffer, seam_profile, seam_blend with depth blur), seam (clean_profile, crossings, caps).

## Seam status (seam.json)
- Path at y=1678: left 368.05 (dx/dy -0.104, d2 -0.0036), cream right 660.13, band 661.29..735.86, cream 292, band 74.6.
- Top visible feature per x on the last row: frontTrees ground + fern mounds 0-177 (dark mounds 38-153), pines ground
  177-367, path 367-660 (cut pebble 555-607), band 660-736, meadow 736-772, frontTrees ground 772-885 (shadowed),
  tree hem lobes 885-937.
- Implemented: path/band edge continuity (exact at y=0, blended over 160 u), colour continuity for ground/cream/band
  (clean per-region profiles, depth-blurred), pebble cap. To do in Stage 2.1: tree-lobe caps (885-937), fern-mound caps
  (38-153), ground texture under the right tree near the seam (above the seam it is mottled shadow).

## Decisions
- Composition (style_spec §4): A join 0-560 (path left, band right->left at ~220), B denser 560-1120 (path right, old
  rooted tree on the right x 560-937), C glade 1120-1678 (path back to ~450, stream on the left from the left edge ~1180
  to the bottom edge).
- Layer mapping: style_spec §5 / recipes.json. Unused: hedge, bridge, doorBush, log; empty: door, stones, fox.
- Scroll: one vertical ScrollView, two stacked segments, s = max(W/937, H/1678) rounded up so 1678*s*displayScale is an
  integer (no-op on phones); initial offset = the current centred crop (0 on phones). Segment 1 =
  `ForestPathArt.image(of:size:(W, 1678 s),scale:)` (its fillTransform then gives exactly scale s, top-aligned).
- Pending approval: drop `private` on `ShapeRaster` and `ShapeDataReader` in ForestPathIllustration.swift so the
  extension uses the identical rasteriser/parser (alternative: duplicate ~200 lines in ForestPathExtension.swift).

## Next steps (Stage 2)
1. Seam caps (tree lobes, fern mounds) + right-tree continuation + ground shadows near the seam; numeric seam check.
2. First third: fern mounds, fern-pine, boulder, clumps with flowers, right bell-tree group; halos/shadows in ground.
3. Swift: ForestPathExtension.swift (data + rasteriser use), scroll host in HomeSceneView; build; simulator render.
4. Checkpoint: seam + first third (stop for approval).
