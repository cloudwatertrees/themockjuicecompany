"""Per-shape and per-layer metrics shared by stats (step 2), the reconstruction test and Stage 2 comparisons."""
import numpy as np
from .core import *

def perimeter(s):
    return sum(float(np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1).sum()) for P in polys(s))

def n_segments(s):
    return sum(len(seg) - 1 for seg in s.subs)

def mesh_cells(s):
    return (s.nx - 1) * (s.ny - 1) if s.nx else 0

def turning(s):
    """Mean |turning angle| per unit length (rad/unit) on the 1x flattening and the share of corners > 45 deg:
    outline smoothness."""
    tot, L, sharp, n = 0.0, 0.0, 0, 0
    for P in polys(s, 1.0):
        Q = P[np.r_[True, np.linalg.norm(np.diff(P, axis=0), axis=1) > 0.05]]
        if len(Q) < 4: continue
        d = np.diff(np.vstack([Q, Q[:1]]), axis=0); l = np.linalg.norm(d, axis=1); d = d / np.maximum(l, 1e-9)[:, None]
        ang = np.arctan2(d[:, 0] * np.roll(d, -1, 0)[:, 1] - d[:, 1] * np.roll(d, -1, 0)[:, 0], (d * np.roll(d, -1, 0)).sum(1))
        tot += np.abs(ang).sum(); L += l.sum(); sharp += int((np.abs(ang) > np.pi / 4).sum()); n += len(ang)
    return (tot / L if L else 0.0), (sharp / n if n else 0.0)

def mesh_gradient(s):
    """Least-squares plane through the mesh vertex L* values: (gx, gy) in L*/unit, and the mesh's L* range."""
    if not s.nx: return None
    x0, y0, x1, y1 = s.box
    gx, gy = np.meshgrid(np.linspace(x0, x1, s.nx), np.linspace(y0, y1, s.ny))
    L = rgb2lab(s.cols)[:, 0]
    A = np.c_[gx.ravel(), gy.ravel(), np.ones(gx.size)]
    c, *_ = np.linalg.lstsq(A, L, rcond=None)
    return c[0], c[1], float(L.max() - L.min())

def lab_of(s):
    return rgb2lab(s.cols)

def describe(s):
    A = area(s); P = perimeter(s); b = tbox(s)
    tr, sh = turning(s)
    g = mesh_gradient(s)
    return dict(area=A, perim=P, width=2 * A / P if P else 0, bw=b[2] - b[0], bh=b[3] - b[1], segs=n_segments(s),
                cells=mesh_cells(s), nx=s.nx, ny=s.ny, turn=tr, sharp=sh, grad=g, lab=rgb2lab(mean_rgb(s)))

def angle_deg(gx, gy):
    """Image-space direction (y down) as a compass-like angle: 0 = right, 90 = up, 180 = left, 270 = down."""
    return float(np.degrees(np.arctan2(-gy, gx)) % 360)

def light_direction(shapes):
    """Area-weighted mean direction of increasing L* over mesh shapes (unit vectors weighted by area x |grad|)."""
    v = np.zeros(2); wsum = 0
    for s in shapes:
        g = mesh_gradient(s)
        if g is None: continue
        gx, gy, rng = g; n = np.hypot(gx, gy)
        if n < 1e-6: continue
        w = area(s) * n
        v += w * np.array([gx, gy]) / n; wsum += w
    if wsum == 0: return None, 0.0
    v /= wsum
    return angle_deg(*v), float(np.linalg.norm(v))   # angle and coherence (0..1)
