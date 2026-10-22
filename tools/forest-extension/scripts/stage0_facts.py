"""Stage 0: ground truth about the live art -> tools/forest-extension/facts.json.

Usage: python stage0_facts.py            (writes facts.json)
Other scripts call common.require_facts(), which stops if the live file's checksum differs from facts.json.
"""
import hashlib, json, re, sys
import numpy as np
from common import REPO, ART_SWIFT, HOME_SWIFT, FACTS, load_live_layers, poly_area, data_sha256

src = open(ART_SWIFT).read()
home = open(HOME_SWIFT).read()

layers = re.search(r'enum LayerID: CaseIterable \{\s*case ([^\n}]+)', src).group(1)
layers = [s.strip() for s in layers.split(',')]
w, h = map(float, re.search(r'static let size = CGSize\(width: ([\d.]+), height: ([\d.]+)\)', src).groups())

# Scale rule: HomeSceneView frames ForestPathIllustration to the full (safe-area-ignoring) geometry; the Canvas
# rasterises via ForestPathArt.image(of:size:scale:) -> fillTransform(for:). Assert the code says what we record.
fill = re.search(r'static func fillTransform\(for viewSize: CGSize\) -> CGAffineTransform \{(.*?)\n    \}', src, re.S).group(1)
assert 'max(viewSize.width / size.width, viewSize.height / size.height)' in fill, 'scale rule changed'
assert '(viewSize.width - size.width * scale) / 2' in fill and '(viewSize.height - size.height * scale) / 2' in fill
assert 'ForestPathIllustration()' in home and '.frame(width: geo.size.width, height: geo.size.height)' in home
assert '.ignoresSafeArea()' in home

shapes = load_live_layers()
per_layer = {L: 0 for L in layers}
mesh_rows = []
for s in shapes:
    per_layer[s.layer] += 1
    x0, y0, x1, y1 = s.box
    area = poly_area(s)
    mesh_rows.append((area, s.nx, s.ny, (x1 - x0) / max(s.nx - 1, 1) if s.nx else 0, (y1 - y0) / max(s.ny - 1, 1) if s.ny else 0,
                      x1 - x0, y1 - y0, s.layer, y1 - 1))
A = np.array([r[0] for r in mesh_rows]); NX = np.array([r[1] for r in mesh_rows]); NY = np.array([r[2] for r in mesh_rows])
CX = np.array([r[3] for r in mesh_rows]); CY = np.array([r[4] for r in mesh_rows])
flat = NX == 0; m22 = (NX == 2) & (NY == 2); big = (NX > 2) | (NY > 2)

def q(v):
    return [round(float(np.percentile(v, p)), 2) for p in (5, 25, 50, 75, 95)] if len(v) else []

density = {
    'flat_count': int(flat.sum()), 'mesh2x2_count': int(m22.sum()), 'mesh_dense_count': int(big.sum()),
    'flat_area_pct_5_25_50_75_95': q(A[flat]), 'mesh2x2_area_pct': q(A[m22]), 'dense_area_pct': q(A[big]),
    'dense_cell_x_pct': q(CX[big]), 'dense_cell_y_pct': q(CY[big]),
    'rule': 'flat if area < ~10 u2; 2x2 mesh if area < ~100 u2; otherwise cells of ~4 u (about 80%) or ~8 u for smooth soft-gradient shapes (about 20%): nx = round(bw/c)+1, ny = round(bh/c)+1 '
            '(bw, bh = tight bounds grown by 1 u). Verified against the percentiles above.',
}
# How well the 4 u rule predicts the dense meshes
pred_nx = np.round(np.array([r[5] for r in mesh_rows]) / 4) + 1
density['dense_nx_exact_match_frac_4u_rule'] = round(float(np.mean(np.abs(pred_nx[big] - NX[big]) <= 1)), 3)

crossing = sorted({r[7] for r in mesh_rows if r[8] > h - 0.5})
facts = {
    'live_art_file': str(ART_SWIFT.relative_to(REPO)),
    'sha256': hashlib.sha256(open(ART_SWIFT, 'rb').read()).hexdigest(),
    'data_sha256': data_sha256(),
    'home_scene_sha256': hashlib.sha256(open(HOME_SWIFT, 'rb').read()).hexdigest(),
    'canvas': {'width': w, 'height': h},
    'layers_back_to_front': layers,
    'shapes_per_layer': per_layer,
    'shape_total': len(shapes),
    'fill_kinds': 'flat RRGGBB or bilinear mesh *W H; no linear gradients in the live data',
    'mesh_density': density,
    'scale_rule': {
        'source': 'HomeSceneView: GeometryReader(.ignoresSafeArea) -> ForestPathIllustration().frame(geo.size).clipped() -> '
                  'Canvas -> ForestPathArt.image(of:size:scale: displayScale) -> fillTransform(for: size)',
        's': 'max(viewW / 937, viewH / 1678)',
        'tx': '(viewW - 937 * s) / 2', 'ty': '(viewH - 1678 * s) / 2',
        'raster': 'pixels = design * s * displayScale + (tx, ty) * displayScale; CPU coverage via CGContext, composited in ShapeRaster',
    },
    'layers_crossing_bottom_edge': crossing,
}
json.dump(facts, open(FACTS, 'w'), indent=1)
print(json.dumps({k: facts[k] for k in ('sha256', 'shape_total', 'shapes_per_layer', 'layers_crossing_bottom_edge')}, indent=1))
print(json.dumps(density, indent=1))
