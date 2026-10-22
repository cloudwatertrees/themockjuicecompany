"""Geometry: smooth outlines from polylines or signed-distance grids, written in the art's path syntax
(absolute M, relative c, one decimal, Z)."""
import numpy as np
from skimage import measure


def resample(P, step, closed=True):
    """Polyline resampled at ~even arc-length spacing `step` (keeps the first point)."""
    P = np.asarray(P, float)
    Q = np.vstack([P, P[:1]]) if closed else P
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(Q, axis=0).T))]
    n = max(int(np.ceil(d[-1] / step)), 3 if closed else 1)
    t = np.linspace(0, d[-1], n, endpoint=not closed) if not closed else np.linspace(0, d[-1], n + 1)[:-1]
    return np.c_[np.interp(t, d, Q[:, 0]), np.interp(t, d, Q[:, 1])]


def adaptive_resample(P, step, min_step=0.8, closed=True):
    """Resample with spacing shrinking where the outline turns sharply (keeps notches and lobe tips)."""
    Q = resample(P, min_step, closed)
    n = len(Q)
    a = np.roll(Q, 1, 0) - Q if closed else np.r_[Q[:1] - Q[1:2], Q[:-1] - Q[1:]]
    b = np.roll(Q, -1, 0) - Q if closed else np.r_[Q[1:] - Q[:-1], Q[-1:] - Q[-2:-1]]
    ang = np.pi - np.arccos(np.clip((a * b).sum(1) / (np.hypot(*a.T) * np.hypot(*b.T) + 1e-9), -1, 1))
    curv = ang / min_step                                       # rad per unit
    want = np.clip(0.35 / (curv + 1e-6), min_step, step)        # ~0.35 rad between samples
    keep = [0]; acc = 0.0
    for i in range(1, n):
        acc += min_step
        if acc >= min(want[i], want[keep[-1]]):
            keep.append(i); acc = 0.0
    if not closed and keep[-1] != n - 1:
        keep.append(n - 1)
    return Q[keep]


def catmull_rom(P, closed=True, tension=0.5):
    """Cubic Bézier segments [(p0, c1, c2, p1), ...] through points P (centripetal-ish uniform CR)."""
    P = np.asarray(P, float)
    n = len(P)
    segs = []
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = P[(i - 1) % n] if closed or i > 0 else P[0]
        p1 = P[i]; p2 = P[(i + 1) % n]
        p3 = P[(i + 2) % n] if closed or i + 2 < n else P[-1]
        c1 = p1 + (p2 - p0) * tension / 3
        c2 = p2 - (p3 - p1) * tension / 3
        segs.append((p1, c1, c2, p2))
    return segs


def fmt(segs, closed=True):
    """Art path syntax. Relative offsets are taken between rounded absolute points so nothing drifts."""
    r = lambda v: np.round(np.asarray(v) * 10).astype(int)
    p = r(segs[0][0])
    out = ['M%s %s' % (_n(p[0]), _n(p[1]))]
    for _, c1, c2, p1 in segs:
        a, b, q = r(c1) - p, r(c2) - p, r(p1)
        d = q - p
        out.append('c%s %s %s %s %s %s' % tuple(_n(v) for v in (a[0], a[1], b[0], b[1], d[0], d[1])))
        p = q
    if closed:
        out.append('Z')
    return ''.join(out)


def _n(v10):
    """Integer tenths -> shortest decimal string."""
    s = '-' if v10 < 0 else ''
    v10 = abs(int(v10))
    return s + (str(v10 // 10) if v10 % 10 == 0 else '%d.%d' % (v10 // 10, v10 % 10))


def poly_path(P, step=2.5, closed=True, adaptive=True):
    Q = adaptive_resample(P, step, closed=closed) if adaptive else resample(P, step, closed)
    return fmt(catmull_rom(Q, closed), closed)


def multi_path(polys, step=2.5):
    return ''.join(poly_path(P, step) for P in polys)


class Grid:
    """Sampling grid over a design-space box at `res` samples per unit."""
    def __init__(self, x0, y0, x1, y1, res=4.0):
        self.x0, self.y0, self.res = x0, y0, res
        self.nx = int(np.ceil((x1 - x0) * res)) + 1
        self.ny = int(np.ceil((y1 - y0) * res)) + 1
        self.X, self.Y = np.meshgrid(x0 + np.arange(self.nx) / res, y0 + np.arange(self.ny) / res)

    def contours(self, sdf, level=0.0, min_area=1.0):
        """Closed outlines of {sdf < level} as design-space polylines (outer and holes; even-odd friendly)."""
        F = np.pad(sdf, 1, constant_values=max(sdf.max(), level + 1))
        out = []
        for C in measure.find_contours(F, level):
            P = np.c_[self.x0 + (C[:, 1] - 1) / self.res, self.y0 + (C[:, 0] - 1) / self.res]
            if len(P) < 4:
                continue
            a = 0.5 * abs(np.dot(P[:, 0], np.roll(P[:, 1], -1)) - np.dot(P[:, 1], np.roll(P[:, 0], -1)))
            if a >= min_area:
                out.append(P[:-1] if np.allclose(P[0], P[-1]) else P)
        return out


# ---- signed distance primitives (negative inside) -------------------------------------------------------------

def sd_circle(X, Y, cx, cy, r):
    return np.hypot(X - cx, Y - cy) - r


def sd_ellipse(X, Y, cx, cy, rx, ry, ang=0.0):
    c, s = np.cos(ang), np.sin(ang)
    u = ((X - cx) * c + (Y - cy) * s) / rx
    v = (-(X - cx) * s + (Y - cy) * c) / ry
    k = np.hypot(u, v)
    return (k - 1) * np.minimum(rx, ry) * np.where(k > 1, 1, 1)


def sd_poly(X, Y, P):
    """Signed distance to a closed polygon (negative inside), vectorised over the grid."""
    P = np.asarray(P, float)
    d = np.full(X.shape, np.inf); inside = np.zeros(X.shape, bool)
    for (ax, ay), (bx, by) in zip(P, np.roll(P, -1, 0)):
        ex, ey = bx - ax, by - ay
        wx, wy = X - ax, Y - ay
        t = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey + 1e-12), 0, 1)
        d = np.minimum(d, np.hypot(wx - ex * t, wy - ey * t))
        cond = ((ay > Y) != (by > Y)) & (X < ax + (Y - ay) * ex / (ey + 1e-12))
        inside ^= cond
    return np.where(inside, -d, d)


def smin(a, b, k):
    """Polynomial smooth minimum (union with fillet radius ~k)."""
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def union(ds, k=0.0):
    out = ds[0]
    for d in ds[1:]:
        out = smin(out, d, k)
    return out


def sd_uneven_capsule(X, Y, ax, ay, bx, by, r1, r2):
    """Rounded cone from (ax, ay) radius r1 to (bx, by) radius r2 (iq's sdUnevenCapsule)."""
    dx, dy = bx - ax, by - ay
    h = np.hypot(dx, dy) + 1e-9
    ux, uy = dx / h, dy / h
    px = np.abs((X - ax) * uy - (Y - ay) * ux)
    py = (X - ax) * ux + (Y - ay) * uy
    b = (r1 - r2) / h
    a = np.sqrt(max(1 - b * b, 1e-6))
    k = -b * px + a * py
    d_mid = a * px + b * py - r1
    d0 = np.hypot(px, py) - r1
    d1 = np.hypot(px, py - h) - r2
    return np.where(k < 0, d0, np.where(k > a * h, d1, d_mid))
