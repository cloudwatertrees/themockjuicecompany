"""Numeric join test, reproducing the app: segment frame (W, segH) with segH = ceil(1678 s ds) / ds, s = max(W/937,
H/1678); each segment rasterised with fillTransform(for: (W, segH)) at display scale ds; live segment's last rows
stacked on the extension segment's first rows.

For each device x scale: row-to-row mean |diff| (0..255) across the join vs the median and p95 of the same measure over
the 16 rows on each side. A step = join diff > max(2 x p95 of neighbours, p95 + 6). Writes strips for the cases that
step (or all with 'all'). usage: python jointest.py [all]"""
import sys, json, math
import numpy as np
from common import *
import pbrender
from extdata import load_ext_layers

DEVICES = [(393, 852), (402, 874), (820, 1180)]
SCALES = [1, 2, 3]
N = 16

live = load_live_layers()
ext = load_ext_layers()
live_strip = [s for s in live if s.box[3] > H - 40]
ext_strip = [s for s in ext if s.box[1] < 40]
res = []
for (Wd, Hd) in DEVICES:
    for ds in SCALES:
        s = max(Wd / W, Hd / H)
        segH = math.ceil(H * s * ds - 1e-9) / ds
        sc = max(Wd / W, segH / H)                       # fillTransform for the segment frame
        tx = (Wd - W * sc) / 2
        ty = (segH - H * sc) / 2
        Wp, Hp = int(math.ceil(Wd * ds - 1e-9)), int(math.ceil(segH * ds - 1e-9))
        k = sc * ds
        # live: last N+1 rows of the segment; ext: first N+1 rows
        a = pbrender.render(live_strip, k, tx * ds, ty * ds - (Hp - (N + 1)), Wp, N + 1, S=8)
        b = pbrender.render(ext_strip, k, tx * ds, ty * ds, Wp, N + 1, S=8)
        img = np.concatenate([a, b], 0) * 255
        d = np.abs(np.diff(img, axis=0)).mean((1, 2))      # row-to-row differences; join = index N
        nb = np.r_[d[:N], d[N + 1:]]
        j = d[N]
        p95 = np.percentile(nb, 95)
        # local: 24-px column bins; join diff per bin vs that bin's own neighbour p95
        bins = max(Wp // (24 * ds), 1)
        cols = np.array_split(np.abs(np.diff(img, axis=0)).mean(2), bins, axis=1)
        local = []
        for c in cols:
            dc = c.mean(1); nbc = np.r_[dc[:N], dc[N + 1:]]
            local.append(dc[N] - max(2 * np.percentile(nbc, 95), np.percentile(nbc, 95) + 6))
        worst = int(np.argmax(local))
        step = j > max(2 * p95, p95 + 6) or max(local) > 0
        res.append({'device': f'{Wd}x{Hd}', 'scale': ds, 'seg_px': [Wp, Hp], 'art_scale_pt_per_u': round(sc, 6),
                    'join_diff': round(float(j), 2), 'neighbour_median': round(float(np.median(nb)), 2),
                    'neighbour_p95': round(float(p95), 2),
                    'worst_bin_excess': round(float(max(local)), 2), 'worst_bin_x_pt': round(worst * Wd / bins, 0), 'step': bool(step)})
        if step or 'all' in sys.argv:
            save(np.repeat(np.repeat(img / 255, 3, 0), 1, 1)[:, :1500], SCRATCH / f'join_{Wd}x{Hd}@{ds}.png')
        print(res[-1])
json.dump(res, open(EXT / 'jointest.json', 'w'), indent=1)
