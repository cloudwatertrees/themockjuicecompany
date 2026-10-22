"""Stage 1.2: seam analysis of the live art's bottom edge -> tools/forest-extension/seam.json.

Measures, on the composite render, the path's visible edges row by row over the bottom 380 u, fits each edge near the seam
(x, dx/dy, d2x/dy2 at y = 1678), records the colour profile of the last row, and lists every shape cut by the bottom edge
with its cross-section intervals at y = 1678.
"""
import json
import numpy as np
from common import *
from art import rasterize

facts = require_facts()
shapes = load_live_layers()
SC = 4.0
Y0 = 1300
box = (0, Y0, W, H)
img = render(in_box(shapes, box, 10), SC, box, S=4)            # (rows, cols, 3) at 4 px/u
rgb = img * 255
R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
cream = (R > 232) & (G > 212) & (B > 175) & (R - B < 70)       # path surface (and pebbles are darker; filled below)
brown = (R > 140) & (R < 200) & (G > 95) & (G < 150) & (B > 70) & (B < 125) & (R - G > 35)


def runs(mask):
    xs = np.where(mask)[0]
    if not len(xs):
        return []
    br = np.where(np.diff(xs) > 1)[0]
    return [(xs[a], xs[b]) for a, b in zip(np.r_[0, br + 1], np.r_[br, len(xs) - 1])]


def merged_run(mask, x_in, gap):
    """Run of `mask` containing column x_in after closing gaps shorter than `gap` px."""
    rs = runs(mask)
    m = []
    for r in rs:
        if m and r[0] - m[-1][1] <= gap:
            m[-1] = (m[-1][0], r[1])
        else:
            m.append(r)
    for r in m:
        if r[0] <= x_in <= r[1]:
            return r
    return None


rows = []
for j in range(0, img.shape[0], 4):
    y = Y0 + (j + 0.5) / SC
    # path centre near the seam is x ~ 500; follow it upwards via the previous row's run midpoint
    xin = int(((rows[-1]['path_left'] + rows[-1]['cream_right']) / 2 if rows else 500) * SC) if False else None
    rows.append({'y': round(y, 2), 'j': j})
# second pass from the bottom up, tracking the run
prev = 500 * SC
for r in reversed(rows):
    j = r.pop('j')
    c = merged_run(cream[j] | (img[j].sum(-1) * 255 > 3 * 205) & ~brown[j], int(prev), int(40 * SC))
    if c is None:
        r['path_left'] = r['cream_right'] = r['band_left'] = r['band_right'] = None
        continue
    prev = (c[0] + c[1]) / 2
    b = merged_run(brown[j], int(c[1] + 6 * SC), int(10 * SC))
    r.update({'path_left': round(c[0] / SC, 2), 'cream_right': round(c[1] / SC, 2),
              'band_left': round(b[0] / SC, 2) if b else None, 'band_right': round(b[1] / SC, 2) if b else None})
rows = [r for r in rows if r['path_left'] is not None]


def fit(key, ylo=1630):
    ys = np.array([r['y'] for r in rows if r[key] is not None and r['y'] >= ylo])
    xs = np.array([r[key] for r in rows if r[key] is not None and r['y'] >= ylo])
    keep = np.ones(len(ys), bool)
    for _ in range(3):                                          # clip rows where flowers/leaves touch the edge
        p = np.polyfit(ys[keep] - H, xs[keep], 2)
        res = xs - np.polyval(p, ys - H)
        keep = np.abs(res) < max(3 * np.std(res[keep]), 0.5)
    res = res[keep]; ys = ys[keep]
    return {'x': round(float(p[2]), 2), 'dxdy': round(float(p[1]), 4), 'd2xdy2': round(float(2 * p[0]), 6),
            'rms_resid': round(float(np.sqrt(np.mean(res ** 2))), 2), 'fit_rows': int(len(ys)), 'y_from': ylo}


edges = {k: fit(k) for k in ('path_left', 'cream_right', 'band_left', 'band_right')}
cl = (edges['path_left']['x'] + edges['band_right']['x']) / 2
centre = {'x_at_seam_incl_band': round(cl, 2), 'width_incl_band': round(edges['band_right']['x'] - edges['path_left']['x'], 2),
          'cream_width': round(edges['cream_right']['x'] - edges['path_left']['x'], 2),
          'band_width': round(edges['band_right']['x'] - edges['band_left']['x'], 2),
          'dxdy': round((edges['path_left']['dxdy'] + edges['band_right']['dxdy']) / 2, 4)}

# colour profile of the last design row (y in [1677, 1678]), 1 u bins
last = img[-int(SC):].mean(0)
from art import rgb2hex
profile = [rgb2hex(last[int(x * SC):int((x + 1) * SC)].mean(0)) for x in range(int(W))]

# shapes cut by the bottom edge: cross-section intervals at y = 1678 (even-odd)
cut = []
for i, s in enumerate(shapes):
    if s.box[3] - 1 <= H or s.box[1] + 1 >= H:
        continue
    xs = []
    for P in flatten(s.subs, 4.0):
        Q = np.vstack([P, P[:1]])
        for (x0, y0), (x1, y1) in zip(Q[:-1], Q[1:]):
            if (y0 <= H) != (y1 <= H):
                xs.append(x0 + (H - y0) * (x1 - x0) / (y1 - y0))
    xs = sorted(xs)
    iv = [(round(a, 1), round(b, 1)) for a, b in zip(xs[0::2], xs[1::2])]
    cut.append({'layer': s.layer, 'index_in_layer': sum(1 for t in shapes[:i] if t.layer == s.layer),
                'fill': 'mesh %dx%d' % (s.nx, s.ny) if s.nx else 'flat ' + rgb2hex(s.cols[0]),
                'bbox': [round(v, 1) for v in (s.box[0] + 1, s.box[1] + 1, s.box[2] - 1, s.box[3] - 1)], 'intervals_at_seam': iv})

seam = {'checksum': facts['sha256'], 'seam_y': H, 'bleed_below_canvas_u': 5,
        'note': 'Edges measured on the composite at 4 px/u by colour class (path run tracked from x=500 upward); fits are quadratics in (y - 1678) over y >= 1630 with 3-sigma clipping.',
        'edges_at_seam': edges, 'path_at_seam': centre, 'edge_rows': rows[::3],
        'cut_shapes': cut, 'last_row_profile_hex_1u': profile}
json.dump(seam, open(EXT / 'seam.json', 'w'), indent=1)
print(json.dumps({'edges': edges, 'path': centre}, indent=1))
print(len(cut), 'cut shapes'); [print(c['layer'], c['index_in_layer'], c['fill'], c['intervals_at_seam']) for c in cut]
