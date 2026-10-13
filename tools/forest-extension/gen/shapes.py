"""Primitive outline constructors shared by all element recipes (closed loops of points, y down, design units)."""
import numpy as np
from .geom import resample_closed, resample_open, Noise1, normals, poly_area

STEP = 3.0          # outline sample spacing: one cubic per ~3 units (original: 30-35 segments per 100 units)

def arc(c, r, a0, a1, n=None):
    """Points on a circle arc from angle a0 to a1 (radians, y-down screen angles: 0 = right, pi/2 = down)."""
    n = n or max(int(abs(a1 - a0) * r / 1.5), 3)
    t = np.linspace(a0, a1, n)
    return np.c_[c[0] + r * np.cos(t), c[1] + r * np.sin(t)]

def finish(P, rng=None, wob=0.0, step=STEP, k1=None):
    """Resample a closed loop at `step` and add a small smooth wobble (units) like traced outlines."""
    P = resample_closed(np.asarray(P, float), step)
    if wob > 0 and rng is not None:
        n = len(P); N = normals(P)
        f = Noise1(rng, 3, k1 or max(6, n // 3), 1.0)
        w = f(np.arange(n) / n); w = w / max(np.abs(w).max(), 1e-9) * wob
        P = P + N * w[:, None]
    return P if poly_area(P) > 0 else P[::-1]

def leaflet(base, tip, width, rng=None, bend=0.0, blunt=0.15, asym=0.0):
    """Pointed leaf from `base` to `tip`, max width at ~35% of the length; `bend` curves the spine sideways
    (fraction of length), `blunt` rounds the tip (0 = pointed, 1 = round end)."""
    base, tip = np.asarray(base, float), np.asarray(tip, float)
    d = tip - base; L = np.linalg.norm(d); t_ = d / L; n_ = np.array([-t_[1], t_[0]])
    s = np.linspace(0, 1, 24)
    spine = base + np.outer(s, d) + np.outer(bend * L * np.sin(np.pi * s), n_)
    pointed = np.sin(np.pi * np.clip(s, 0, 1) ** 0.75) ** 0.9
    rounded = np.sqrt(np.clip(1 - ((s - 0.45) / 0.55) ** 2, 0, 1)) * np.clip(s / 0.12, 0, 1) ** 0.5
    prof = width / 2 * ((1 - blunt) * pointed + blunt * rounded)
    prof[-1] = 0
    left = spine + np.outer(prof * (1 + asym), n_); right = spine - np.outer(prof * (1 - asym), n_)
    return np.vstack([left, right[::-1][1:-1]])

def lobe_chain(a, b, n, depth, rng, jitter=0.25, outward=1.0):
    """Scalloped edge points from a to b with n round lobes bulging to the right of a->b (screen coords)."""
    a, b = np.asarray(a, float), np.asarray(b, float); d = b - a; L = np.linalg.norm(d)
    t_ = d / L; nr = np.array([-t_[1], t_[0]]) * outward
    w = rng.uniform(1 - jitter, 1 + jitter, n); w /= w.sum(); e = np.r_[0, np.cumsum(w)]
    pts = []
    for i in range(n):
        h = depth * rng.uniform(1 - jitter, 1 + jitter)
        for u in np.linspace(0, 1, 9)[:-1]:
            pts.append(a + d * (e[i] + (e[i + 1] - e[i]) * u) + nr * h * np.sin(np.pi * u) ** 0.8)
    pts.append(b)
    return np.array(pts)

def scallop_y(x, x0, x1, y0, n, depth, phase=0.0):
    """Lobed edge as a function y(x) between x0 and x1 (n lobes, bulging down by `depth`), for shading terms."""
    u = np.clip((np.asarray(x, float) - x0) / max(x1 - x0, 1e-9), 0, 1)
    return y0 + depth * np.abs(np.sin(np.pi * (u * n + phase))) ** 0.8

def thin_strip(C, w, rng=None, taper=0.3, side=1.0):
    """Closed rim strip along an open polyline C, width w tapering to the ends, on `side` (+1 left normal)."""
    C = resample_open(np.asarray(C, float), max(int(np.linalg.norm(np.diff(C, axis=0), axis=1).sum() / 1.2), 4))
    n = len(C); N = normals(C, closed=False); s = np.linspace(0, 1, n)
    prof = np.clip(np.minimum(s, 1 - s) / taper, 0, 1) ** 0.6 * w
    if rng is not None: prof = prof * rng.uniform(0.8, 1.2)
    O = C + N * (prof * side)[:, None]
    return np.vstack([C, O[::-1]])

def sub_curve(P, i0, i1):
    """Points of closed loop P from index i0 to i1 inclusive (wrapping)."""
    n = len(P)
    if i1 >= i0: return P[i0:i1 + 1]
    return np.vstack([P[i0:], P[:i1 + 1]])
