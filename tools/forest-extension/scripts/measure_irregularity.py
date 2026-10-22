"""Step 2: measure the live art's painted irregularity -> tools/forest-extension/irregularity.json.

(a) colour mottling: residual of each dense mesh (vertices inside the shape) against its own smooth fit (Gaussian,
    sigma 12 u): luminance std and correlation length, per layer and tone tertile;
(b) outline irregularity: turning angles of outlines resampled at 1 u and 4 u, segments per 100 u, per layer;
(c) asymmetry: 1 - IoU(silhouette, mirrored about its centroid x) for large shapes; lobe-length variation;
(d) region-edge offset: for shapes nested inside a larger same-layer shape, distance of the inner outline to the outer
    outline (mean, std, std/mean) where the inner edge is interior;
(e) ground shadows: ground luminance vs distance to foliage, below vs above objects.
Functions take a list of PShapes so the same table can be computed for extension output (python ... ext).
"""
import json, sys
import numpy as np
from scipy import ndimage as ndi
from common import *
from art import rasterize
from fx.paint import _inside, area
from fx.geom import resample

LUM = np.array([0.299, 0.587, 0.114]) * 255


def mottling(shapes):
    rows = {}
    for s in shapes:
        if s.nx < 6 or s.ny < 6:
            continue
        x0, y0, x1, y1 = s.box
        cx, cy = (x1 - x0) / (s.nx - 1), (y1 - y0) / (s.ny - 1)
        X, Y = np.meshgrid(np.linspace(x0, x1, s.nx), np.linspace(y0, y1, s.ny))
        inside = _inside(s.subs, X, Y)
        if inside.sum() < 25:
            continue
        L = (s.cols.reshape(s.ny, s.nx, 3) @ LUM)
        sig = 12.0 / max(cx, 1e-6)
        w = ndi.gaussian_filter(inside.astype(float), sig)
        smooth = ndi.gaussian_filter(L * inside, sig) / np.maximum(w, 1e-6)
        r = (L - smooth) * inside
        amp = float(r[inside].std())
        # correlation length along x: lag (u) where the autocorrelation of the residual falls below 1/e
        ac = []
        for lag in range(0, min(s.nx // 2, 12)):
            a = r[:, :s.nx - lag][inside[:, :s.nx - lag] & inside[:, lag:]]
            b = r[:, lag:][inside[:, :s.nx - lag] & inside[:, lag:]]
            if len(a) < 10: break
            ac.append(np.corrcoef(a, b)[0, 1] if lag else 1.0)
        ac = np.array(ac)
        below = np.where(ac < 1 / np.e)[0]
        corr = float(below[0] * cx) if len(below) else float(len(ac) * cx)
        tone = float(L[inside].mean())
        rows.setdefault(s.layer, []).append((amp, corr, tone))
    out = {}
    for L, v in rows.items():
        v = np.array(v)
        t = np.percentile(v[:, 2], [33, 67])
        def summ(m):
            return {'n': int(m.sum()), 'amp_lum_median': round(float(np.median(v[m, 0])), 2),
                    'amp_lum_p90': round(float(np.percentile(v[m, 0], 90)), 2), 'corr_len_u_median': round(float(np.median(v[m, 1])), 1)}
        out[L] = {'all': summ(np.ones(len(v), bool)), 'dark': summ(v[:, 2] <= t[0]), 'mid': summ((v[:, 2] > t[0]) & (v[:, 2] <= t[1])),
                  'light': summ(v[:, 2] > t[1])}
    return out


def outlines(shapes, min_len=40):
    rows = {}
    for s in shapes:
        polys = flatten(s.subs, 4.0)
        nseg = sum(len(seg) - 1 for seg in s.subs)
        for P in polys:
            Lp = np.hypot(*np.diff(np.vstack([P, P[:1]]), axis=0).T).sum()
            if Lp < min_len:
                continue
            d = {}
            for step in (1.0, 4.0):
                Q = resample(P, step)
                a = np.diff(np.unwrap(np.arctan2(*np.diff(np.vstack([Q, Q[:2]]), axis=0).T[::-1])))
                d[step] = np.degrees(np.abs(a))
            rows.setdefault(s.layer, []).append((d[1.0], d[4.0], nseg / Lp * 100 if len(polys) == 1 else np.nan, Lp))
    out = {}
    for L, v in rows.items():
        t1 = np.concatenate([r[0] for r in v]); t4 = np.concatenate([r[1] for r in v])
        seg = np.array([r[2] for r in v]); seg = seg[np.isfinite(seg)]
        out[L] = {'n_outlines': len(v), 'turn_1u_deg_p50_p90_p99': [round(float(np.percentile(t1, p)), 2) for p in (50, 90, 99)],
                  'turn_4u_deg_p50_p90_p99': [round(float(np.percentile(t4, p)), 2) for p in (50, 90, 99)],
                  'frac_1u_turns_over_10deg': round(float((t1 > 10).mean()), 4),
                  'segments_per_100u_median': round(float(np.median(seg)), 1) if len(seg) else None}
    return out


def mask_of(s, res=1.0):
    x0, y0, x1, y1 = s.box
    Wp, Hp = int((x1 - x0) * res) + 2, int((y1 - y0) * res) + 2
    r = rasterize(flatten(s.subs, res), res, -x0 * res, -y0 * res, Wp, Hp, 2)
    m = np.zeros((Hp, Wp))
    if r:
        a, b, c = r; h, w = c.shape; m[b:b + h, a:a + w] = c
    return m > 0.5


def asymmetry(shapes, layers=('frontTrees', 'backTrees', 'pines', 'bushes', 'rocks'), min_area=1500):
    rows = {}
    for s in shapes:
        if s.layer not in layers or area(s.subs) < min_area:
            continue
        m = mask_of(s)
        if m.sum() < 50:
            continue
        ys, xs = np.nonzero(m)
        cx = xs.mean()
        mx = np.round(2 * cx - xs).astype(int)
        ok = (mx >= 0) & (mx < m.shape[1])
        mir = np.zeros_like(m); mir[ys[ok], mx[ok]] = True
        iou = (m & mir).sum() / max((m | mir).sum(), 1)
        rows.setdefault(s.layer, []).append(1 - iou)
    return {L: {'n': len(v), 'asym_median': round(float(np.median(v)), 3), 'asym_p25_p75': [round(float(np.percentile(v, p)), 3) for p in (25, 75)]}
            for L, v in rows.items()}


def lobe_variation(shapes, layers=('frontTrees', 'backTrees', 'pines', 'bushes'), min_area=800):
    """Lobes = outline stretches between concave notches (turning < -25 deg over 3 u): CV of lobe lengths per shape."""
    rows = {}
    for s in shapes:
        if s.layer not in layers or area(s.subs) < min_area:
            continue
        for P in flatten(s.subs, 4.0):
            Q = resample(P, 1.0)
            if len(Q) < 60: continue
            sgn = np.sign(np.sum(Q[:, 0] * np.roll(Q[:, 1], -1) - np.roll(Q[:, 0], -1) * Q[:, 1]))
            ang = np.unwrap(np.arctan2(*np.diff(np.vstack([Q, Q[:1]]), axis=0).T[::-1]))
            turn3 = (np.roll(ang, -2) - ang) * sgn
            notch = np.where(turn3 < -np.radians(25))[0]
            if len(notch) < 4: continue
            groups = np.split(notch, np.where(np.diff(notch) > 3)[0] + 1)
            pos = np.array([g[len(g) // 2] for g in groups])
            lengths = np.diff(np.r_[pos, pos[0] + len(Q)])
            lengths = lengths[lengths > 6]
            if len(lengths) >= 3:
                rows.setdefault(s.layer, []).append(lengths.std() / lengths.mean())
    return {L: {'n': len(v), 'lobe_len_cv_median': round(float(np.median(v)), 3)} for L, v in rows.items()}


def region_offsets(shapes, layers=('frontTrees', 'backTrees', 'pines', 'bushes', 'rocks')):
    """Inner tone regions vs the enclosing silhouette: distance of inner outline points to the outer outline."""
    rows = {}
    by = {}
    for s in shapes:
        if s.layer in layers:
            by.setdefault(s.layer, []).append(s)
    for L, ss in by.items():
        big = [s for s in ss if area(s.subs) > 1500]
        for s in ss:
            a = area(s.subs)
            if a < 150: continue
            P = np.vstack([resample(Q, 1.0) for Q in flatten(s.subs, 4.0)])
            for b in big:
                if b is s or area(b.subs) < 1.5 * a: continue
                if not (b.box[0] <= s.box[0] + 2 and b.box[2] >= s.box[2] - 2 and b.box[1] <= s.box[1] + 2 and b.box[3] >= s.box[3] - 2):
                    continue
                ins = _inside(b.subs, P[:, 0], P[:, 1])
                if ins.mean() < 0.85: continue
                B = np.vstack([resample(Q, 1.0) for Q in flatten(b.subs, 4.0)])
                from scipy.spatial import cKDTree
                d, _ = cKDTree(B).query(P)
                dd = d[d > 1.5]
                if len(dd) > 20:
                    rows.setdefault(L, []).append((dd.mean(), dd.std()))
                break
    return {L: {'n': len(v), 'interior_edge_dist_mean_median': round(float(np.median([r[0] for r in v])), 1),
                'std_over_mean_median': round(float(np.median([r[1] / r[0] for r in v])), 3)} for L, v in rows.items()}


def ground_shadows(shapes, box=(0, 0, W, H), res=1.0):
    img = render(shapes, res, box) * 255
    R, G, B = img[..., 0], img[..., 1], img[..., 2]
    ground = (R > 120) & (G > 120) & (B < 200) & (np.abs(R - G) < 40) & (B < G - 15)
    foliage = (G > R + 8) & (G > B + 15) & ~ground
    lum = img @ (LUM / 255)
    dist = ndi.distance_transform_edt(~foliage) / res
    # direction: is the nearest foliage above (object casting shadow downward) or below?
    fol_above = ndi.maximum_filter1d(foliage.astype(np.uint8), size=int(30 * res), axis=0, origin=int(14 * res)) > 0
    out = {}
    far = lum[ground & (dist > 40)].mean()
    for a, b in ((0, 3), (3, 6), (6, 10), (10, 16), (16, 25), (25, 40)):
        m = ground & (dist > a) & (dist <= b)
        out[f'{a}-{b}u'] = {'below_obj': round(float(lum[m & fol_above].mean() - far), 1) if (m & fol_above).any() else None,
                            'other': round(float(lum[m & ~fol_above].mean() - far), 1) if (m & ~fol_above).any() else None}
    out['far_ground_lum'] = round(float(far), 1)
    return out


def table(shapes):
    return {'mottling': mottling(shapes), 'outlines': outlines(shapes), 'asymmetry': asymmetry(shapes),
            'lobes': lobe_variation(shapes), 'region_offsets': region_offsets(shapes), 'ground_shadows': ground_shadows(shapes)}


if __name__ == '__main__':
    facts = require_facts()
    if len(sys.argv) > 1 and sys.argv[1] == 'ext':
        from extdata import load_ext_layers
        print(json.dumps(table(load_ext_layers()), indent=1))
    else:
        t = table(load_live_layers())
        t['checksum'] = facts['sha256']
        json.dump(t, open(EXT / 'irregularity.json', 'w'), indent=1)
        print(json.dumps(t, indent=1))
