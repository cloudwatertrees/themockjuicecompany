"""Seam continuation: clean per-region colour profiles of the live art's last row, and caps that continue the
features cut by the bottom edge (pebble, tree lobes, fern mounds) with tangent-matched outlines and fine meshes whose
top row reproduces the live colours exactly."""
import numpy as np
from common import load_live_layers, H
from art import flatten
from .ground import seam_profile
from .geom import fmt, catmull_rom, adaptive_resample
from pbart import PShape


def clean_profile(P, keep):
    """Profile with x outside the `keep` ranges replaced by linear interpolation from the kept columns."""
    xs = np.arange(len(P)) + 0.5
    m = np.zeros(len(P), bool)
    for a, b in keep:
        m |= (xs >= a) & (xs <= b)
    out = P.copy()
    for c in range(3):
        out[~m, c] = np.interp(xs[~m], xs[m], P[m, c])
    return out


def crossings(shape, y=H):
    """x positions where a live shape's outline crosses y, with the outline's unit direction there (pointing down)."""
    out = []
    for P in flatten(shape.subs, 4.0):
        Q = np.vstack([P, P[:1]])
        for (x0, y0), (x1, y1) in zip(Q[:-1], Q[1:]):
            if (y0 <= y) != (y1 <= y):
                x = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
                d = np.array([x1 - x0, y1 - y0]); d = d / (np.hypot(*d) + 1e-12)
                if d[1] < 0:
                    d = -d
                out.append((x, d))
    return sorted(out, key=lambda t: t[0])


def tangent_at(shape, x_near, y=H, span=6.0):
    """Average downward direction of the outline near (x_near, y), from the outline points within `span` above y."""
    best = None
    for P in flatten(shape.subs, 4.0):
        d = np.hypot(P[:, 0] - x_near, P[:, 1] - y)
        i = int(np.argmin(d))
        if best is None or d[i] < best[0]:
            best = (d[i], P, i)
    _, P, i = best
    n = len(P)
    pts = [P[(i + k) % n] for k in range(-40, 41)]
    pts = np.array([p for p in pts if y - span <= p[1] <= y + 0.5])
    if len(pts) < 2:
        return np.array([0.0, 1.0])
    a = np.polyfit(pts[:, 1], pts[:, 0], 1)[0]           # dx/dy
    v = np.array([a, 1.0])
    return v / np.hypot(*v)


def cap_outline(xl, tl, xr, tr, depth, top=-3.0, n=40):
    """Closed outline: from (xl, top) down through the seam with direction tl, round the bottom at ~depth below the
    seam, back up through (xr, 0) with direction tr. Cubic Bézier bottom, straight top above the seam."""
    p0 = np.array([xl, 0.0]); p3 = np.array([xr, 0.0])
    w = xr - xl
    k = depth * 1.33
    p1 = p0 + tl / max(tl[1], 0.2) * k
    p2 = p3 + tr / max(tr[1], 0.2) * k
    t = np.linspace(0, 1, n)[:, None]
    B = (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3
    up_l = np.array([xl - tl[0] / tl[1] * (-top), top])
    up_r = np.array([xr - tr[0] / tr[1] * (-top), top])
    return np.vstack([up_l, B, up_r])


def cap_shape(layer, outline, field, cell=1.0):
    """Shape with a fine mesh (cell u) so that the top rows carry the live colours crisply."""
    Q = adaptive_resample(outline, 1.5, min_step=0.5, closed=True)
    pathstr = fmt(catmull_rom(Q, True))
    from pbart import tight_bounds
    from art import parse_path
    b = tight_bounds(parse_path(pathstr))
    box = (b[0] - 1, b[1] - 1, b[2] + 1, b[3] + 1)
    nx = max(int(round((box[2] - box[0]) / cell)) + 1, 2); ny = max(int(round((box[3] - box[1]) / cell)) + 1, 2)
    X, Y = np.meshgrid(np.linspace(box[0], box[2], nx), np.linspace(box[1], box[3], ny))
    return PShape(layer, pathstr=pathstr, cols=np.clip(field(X, Y).reshape(-1, 3), 0, 1), nx=nx, ny=ny)
