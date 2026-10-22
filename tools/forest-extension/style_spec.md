# Forest extension — style spec (Stage 1)

All facts about the live art come from `facts.json` (checksum `27528256…f04aa3`) and `seam.json`. Coordinates: live art in
design units (937 x 1678); extension in its own space, y = 0 at the seam (live y = 1678).

## 1. Visual language of the live art (what the eye sees)
- **Format.** Filled even-odd shapes, flat or bilinear-mesh colour, no strokes, no gradients other than meshes. Mesh rule:
  flat < ~10 u², 2x2 < ~100 u², otherwise ~4 u cells (≈80 %) or ~8 u cells for smooth soft shapes (≈20 %). Shapes bleed
  5 u past the canvas.
- **Mosaic, not objects.** The art is traced: no base meadow; ground is split across meadow/path/pines/frontTrees
  shapes, and every object layer also carries the ground patch around it. The extension keeps the layer IDs but builds
  clean objects on one ground base (see §4).
- **Light.** Soft, warm, from above, leaning toward the clearing (path column, x ≈ 470): trees and rocks left of it are
  lit on their right, right of it on their left. Undersides are darker; tiers cast a dark band under the tier above.
- **Edges.** Hard antialiased outlines, softened by colour: neighbouring regions are close in value at their boundary,
  so tone changes read as painted regions, not cut-outs. Occasional thin pale rims (path edges, band inner line) and
  darker rims (pebble/hem bottoms).
- **Ground.** Yellow-green meadow `E4DEA1` in the open, greener `C5C777` near vegetation, olive `A5AF67` soft shadows
  under trees and shrubs (soft-edged, painted inside meshes), pale halos `EDE6B3`–`F2EAC0` around some plants and along
  path banks.
- **Silhouettes.** Rounded, scalloped lobes everywhere; leaflets are blunt ovals, never sharp points.

## 2. Element recipes (details in `recipes.json`)
| Element | Live layer | Build | Palette (dark → light) |
|---|---|---|---|
| Bell-tier conifer | frontTrees, backTrees | 2–4 stacked bells: dome (r ≈ 0.45 W), neck, concave flare, hem of 3–4 round lobes; per tier a body shape and a lit-side shape (soft 14 u ramp); lower tiers darker under the hem above | `3A6A5A 467F69 5B9972 7BB77F 9CCB89 B4D592` |
| Fern-pine | pines | 3 leaf-rosette tiers (fans of blunt oval leaflets + front hem lobes), dark core under each tier, pale egg-shaped ground halo | `3C735E 498663 70AD72 94C47F B2D592` |
| Leaf clump / fern | bushes | palmate leaves (rosette fans) radiating from a low centre, back leaves darker, front yellow-green leaves, dark inner mass behind | `426F55 598A60 70A773 82C289 A6D49A`, front `6F9A55 92BC68 B2CF7E` |
| Flower | flowers (+ bushes in live) | 5 round petals in one shape (paler tips/top), yellow centre lit from above; white / lilac / yellow | white `DCDDB8 F3EED2 FCF8E6`, lilac `A57CC0 C995E0 DDB2F0` |
| Boulder | rocks | domed silhouette, faces: light top, dark left, mid front, darker narrow right; optional moss | `6E6E86 8B89A0 9E9BB0 B5B1C0 C9C5D0` |
| Path surface | path | cream mesh `F7E8CC` with fine mottling, darker shoulder next to the band, pale rim `EFE3B4` on band-less edges | `E9D3AC F3DFBE F6E4C3 F7E8CC F9EBD2` |
| Edge band | pathEdges | brown band `B08062` on the outer side of each bend, tapering in/out at inflections, 1.2 u pale line `D3B190` to the cream, pale bank strip outside, lighter cobbles | band `94684B A97A5C B08062 BC8D6D`, cobbles `B88A69 C49874 CFA582` |
| Pebble | path | flat oval, darker lower rim, paler inset | `D9B98F EBD3AE F3DFBF` |
| Pond | pond | blue mesh deeper at the back `52AAD7` → `7CCBEA`, light cyan inner rim, stones on the far bank, lily pads, cattails | `52AAD7 6FC8E6 8FD3EE` |

## 3. Composition of the live art (reference)
- Path: winds through the full height; visible cream width 230–300 u, band 65–80 u; three bends per screen with the band
  switching sides at each inflection.
- Foliage coverage by colour (thirds, top → bottom): 47 % / 26 % / 41 %; path 25 / 20 / 33 %.
- Big masses at the left and right edges (bell trees), mid-size features near the path (pine, bushes, rocks, log,
  bridge), small details everywhere (flowers, grass tufts, pebbles).

## 4. Extension composition (extension y; 1 screen ≈ 1678 u)
| Band | y | Content | Foliage target |
|---|---|---|---|
| A — join | 0–560 | path continues down-left, inflection ~220, leftmost (x ≈ 318) at ~520; band right → tapers out by 290, left band from 200; familiar shrubs: fern mounds and flowers continuing the left seam edge, a fern-pine and a boulder left, bell-tree group continuing the right edge, leaf clumps with flowers | ~42 % |
| B — denser | 560–1120 | path sweeps right (rightmost x ≈ 585 at ~1150); ferns line both path edges, larger clumps, bell trees closer; **old rooted tree** on the right (canopy x 560–937, y ≈ 560–880, trunk + flared roots at y ≈ 880–960) | ~52 % |
| C — glade | 1120–1678 | path eases back toward x ≈ 450; open lighter meadow, trees only at the edges, scattered flowers; **shallow stream** beside the path on the left (enters from the left edge ~y 1180, meanders down 40–70 u from the path's left edge, exits the bottom), smooth stones along and in it, reeds and lily pads at a wider pool | ~30 % (+ water ~8 %) |
Transitions are ramps over ≥ 840 u: density rises from y ≈ 200 to 900, then falls into the glade from 1000 to 1400.

## 5. New elements — approach and layer mapping
| Element | Layer | Approach |
|---|---|---|
| Ferns | bushes | leaf-clump recipe with longer, narrower leaflet fans (pinnate fronds = rosette fingers along an arching axis) |
| Old rooted tree | trunk + roots: backTrees; canopy: frontTrees | bespoke: thick trunk with bark-tone mesh, 5–7 flared roots gripping the ground (SDF union of tapered capsules, lit side lighter), a broad canopy of large scalloped lobes (union of discs, 3 tone regions + dark under-canopy), soft olive ground shadow, moss on roots |
| Stream | pond (water, rim, ripples, pads, reeds) | bespoke: centreline spline with width profile; water mesh deeper blue on the axis, light cyan inner rims, pale sandy bank strip in the meadow field, small light ripple streaks, lily pads/cattails from the pond recipe |
| Smooth stones | rocks | rounded flattened ovals, two-tone (light top, darker lower half), soft shadow/wet rim where in water |
| Ground, halos, shadows | meadow | one full-canvas mesh from a paint buffer (open tone, soft object shadows, halos, bank strips), blended into the live last row at the seam |
| Unused | hedge, bridge, doorBush, door, stones, fox, log | empty in the extension (stones/fox/door are already empty in the live art) |

## 6. Intended differences (each tied to the SCENE brief)
1. More, larger ferns and denser clumps in band B — "gradual denser vegetation".
2. A single large broadleaf tree with exposed roots (no equivalent in the live art) — "old rooted tree landmark".
3. Lighter, more open meadow and fewer tall trees in band C — "peaceful glade".
4. A narrow flowing stream instead of a round pond; stones in the water — "shallow stream beside the path".
5. Path winding is new (inflections at different heights) but width, edge band, cobbles, pebbles and colours are the
   live values — "new composition, same visual language".
6. Clean object layers on one ground base instead of the traced mosaic — invisible to the eye, keeps the layer IDs'
   meaning ("existing layer IDs keep their meaning").

## 7. Seam method
- Path edges: the extension's edges are blended from the measured quadratics of the live edges (exact x, slope and
  curvature at y = 0) into the new centreline over 160 u; band edges ride on the cream edges.
- Colour: every continuous field (ground, cream, band) equals the live last row at y = 0 and eases into its own field;
  the live profile is blurred in proportion to depth so column detail does not drag into streaks. Profiles are cleaned
  per region so cut features do not smear.
- Cut features (the pebble at x 555–607, right tree hem lobes at x 885–937, left fern mounds at x 38–153): caps with
  tangent-matched outlines and 1 u meshes whose top row carries the live colours.
- Join in the app: both segments use the same scale and crop; s is rounded up so each segment is a whole number of
  pixel rows (no-op on phones), and the extension raster starts exactly at the join row.
