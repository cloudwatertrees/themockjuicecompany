"""Outline geometry for the generator: smooth closed curves as cubic Béziers, lobed edges, strips, and the
serialisation into the layer data's SVG subset (M, c, Z with one decimal, relative cubic segments)."""
import numpy as np

# ---------------------------------------------------------------------------------------------------------------
# Curves
def catmull_closed(P, tension=1.0):
    """Closed Catmull-Rom through points P (N,2) -> list of cubic segments (p0, c1, c2, p1).
    tension scales the tangents (1 = uniform Catmull-Rom, <1 tighter)."""
    P = np.asarray(P, float); n = len(P); segs = []
    for i in range(n):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % n], P[(i + 2) % n]
        c1 = p1 + (p2 - p0) * tension / 6; c2 = p2 - (p3 - p1) * tension / 6
        segs.append((p1, c1, c2, p2))
    return segs

def catmull_open(P, tension=1.0):
    P = np.asarray(P, float); n = len(P); segs = []
    for i in range(n - 1):
        p0 = P[i - 1] if i > 0 else 2 * P[0] - P[1]
        p3 = P[i + 2] if i + 2 < n else 2 * P[-1] - P[-2]
        p1, p2 = P[i], P[i + 1]
        segs.append((p1, p1 + (p2 - p0) * tension / 6, p2 - (p3 - p1) * tension / 6, p2))
    return segs

def bez(seg, t):
    p0, c1, c2, p1 = seg; t = np.asarray(t, float)[..., None]; m = 1 - t
    return m ** 3 * p0 + 3 * m * m * t * c1 + 3 * m * t * t * c2 + t ** 3 * p1

def sample(segs, per=12):
    return np.vstack([bez(s, np.linspace(0, 1, per, endpoint=False)) for s in segs])

def resample_closed(P, step):
    """Uniformly resample a closed polyline at arc-length `step`."""
    P = np.asarray(P, float); Q = np.vstack([P, P[:1]])
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    n = max(int(d[-1] / step), 6); t = np.linspace(0, d[-1], n, endpoint=False)
    return np.c_[np.interp(t, d, Q[:, 0]), np.interp(t, d, Q[:, 1])]

def resample_open(P, n):
    P = np.asarray(P, float)
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    t = np.linspace(0, d[-1], n)
    return np.c_[np.interp(t, d, P[:, 0]), np.interp(t, d, P[:, 1])]

def poly_area(P):
    x, y = P[:, 0], P[:, 1]; return 0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

def normals(P, closed=True):
    """Unit normals (left of travel direction in y-down coordinates -> rotate tangent by +90 deg)."""
    if closed: T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    else: T = np.gradient(P, axis=0)
    T = T / np.maximum(np.linalg.norm(T, axis=1), 1e-9)[:, None]
    return np.c_[-T[:, 1], T[:, 0]]

def ccw(P):
    """Points ordered with positive signed area (clockwise on screen with y down)."""
    return P if poly_area(P) > 0 else P[::-1]

# ---------------------------------------------------------------------------------------------------------------
# Noise (deterministic, seeded)
class Noise1:
    """Smooth periodic 1-D noise from random harmonics: f(t), t in [0, 1)."""
    def __init__(self, rng, k0=2, k1=7, amp=1.0, decay=1.0):
        ks = np.arange(k0, k1 + 1)
        self.k = ks; self.a = rng.normal(0, 1, len(ks)) * amp / ks ** decay; self.p = rng.uniform(0, 2 * np.pi, len(ks))
    def __call__(self, t):
        t = np.asarray(t, float)[..., None]
        return (self.a * np.sin(2 * np.pi * self.k * t + self.p)).sum(-1)

class Noise2:
    """Smooth 2-D value noise (bicubic-interpolated random lattice), deterministic per rng."""
    def __init__(self, rng, scale, n=24):
        self.s = float(scale); self.g = rng.normal(0, 1, (n, n)); self.n = n
    def __call__(self, x, y):
        from scipy.ndimage import map_coordinates
        u = (np.asarray(x, float) / self.s) % self.n; v = (np.asarray(y, float) / self.s) % self.n
        return map_coordinates(self.g, [v.ravel(), u.ravel()], order=3, mode='wrap').reshape(np.shape(u))

# ---------------------------------------------------------------------------------------------------------------
# Outline builders (all return closed point loops; smoothed into Béziers at emit time)
def wobble(P, rng, amp, k0=3, k1=12, closed=True):
    """Displace a loop along its normals by smooth noise of amplitude `amp` (units)."""
    P = np.asarray(P, float); N = normals(P, closed); n = len(P)
    f = Noise1(rng, k0, k1, 1.0)
    w = f(np.arange(n) / n); w = w / max(np.abs(w).max(), 1e-9) * amp
    return P + N * w[:, None]

def lobed_curve(a, b, n, depth, rng, jitter=0.25, bulge=1.0, pts_per_lobe=6, sharp=0.35):
    """Scalloped edge from a to b: n round lobes bulging to the right of a->b (y-down: 'down' for a left->right edge).
    depth = lobe height in units; sharp = how pinched the notches between lobes are (0 = sine, 1 = deep cusps)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a; L = np.linalg.norm(d); t_ = d / L; nrm = np.array([-t_[1], t_[0]])
    w = rng.uniform(1 - jitter, 1 + jitter, n); w = w / w.sum()
    edges = np.r_[0, np.cumsum(w)]
    pts = []
    for i in range(n):
        h = depth * rng.uniform(1 - jitter, 1 + jitter) * bulge
        for j in range(pts_per_lobe):
            u = j / pts_per_lobe
            s = edges[i] + (edges[i + 1] - edges[i]) * u
            prof = np.sin(np.pi * u) ** (1 - 0.6 * sharp)       # rounded lobe, pinched notch
            pts.append(a + d * s + nrm * h * prof)
    pts.append(b.copy())
    return np.array(pts)

def ellipse(c, rx, ry, rot=0.0, n=24):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    P = np.c_[rx * np.cos(t), ry * np.sin(t)]
    R = np.array([[np.cos(rot), -np.sin(rot)], [np.sin(rot), np.cos(rot)]])
    return P @ R.T + np.asarray(c, float)

def blob(c, rx, ry, rng, rot=0.0, amp=0.08, n=28, k1=5):
    """Ellipse with smooth radial noise (relative amplitude `amp`)."""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    f = Noise1(rng, 2, k1, 1.0); r = 1 + amp * f(t / (2 * np.pi)) / max(np.abs(f(np.linspace(0, 1, 64))).max(), 1e-9)
    P = np.c_[rx * r * np.cos(t), ry * r * np.sin(t)]
    R = np.array([[np.cos(rot), -np.sin(rot)], [np.sin(rot), np.cos(rot)]])
    return P @ R.T + np.asarray(c, float)

def strip(C, w0, w1=None, side=1.0, taper=0.25):
    """Closed thin strip along open polyline C: from C to C offset by w (tapering to 0 at both ends)."""
    C = np.asarray(C, float); n = len(C); w1 = w0 if w1 is None else w1
    N = normals(C, closed=False)
    s = np.linspace(0, 1, n); w = w0 + (w1 - w0) * s
    tp = np.clip(np.minimum(s, 1 - s) / max(taper, 1e-6), 0, 1); w = w * np.sin(tp * np.pi / 2) ** 0.7
    O = C + N * (w * side)[:, None]
    return np.vstack([C, O[::-1]])

def crescent(c, rx, ry, rot, thick, rng=None, span=0.55):
    """Crescent hugging the lower part of an ellipse: outer arc on the ellipse, inner arc pulled in by `thick`."""
    a0, a1 = np.pi * (0.5 - span), np.pi * (0.5 + span)
    t = np.linspace(a0, a1, 14)
    R = np.array([[np.cos(rot), -np.sin(rot)], [np.sin(rot), np.cos(rot)]])
    outer = np.c_[rx * np.cos(t), ry * np.sin(t)]
    prof = np.sin((t - a0) / (a1 - a0) * np.pi) ** 0.8
    inner = np.c_[(rx - thick * prof) * np.cos(t), (ry - thick * prof * 1.0) * np.sin(t)] - np.c_[0 * t, thick * 0.35 * prof]
    P = np.vstack([outer, inner[::-1][1:-1]])
    return P @ R.T + np.asarray(c, float)

# ---------------------------------------------------------------------------------------------------------------
# Serialisation
def fmt(v):
    s = ('%.1f' % v)
    if s.endswith('.0'): s = s[:-2]
    if s == '-0': s = '0'
    return s

def loop_segments(P, tension=1.0, smooth=True):
    """Closed point loop -> cubic segments. smooth=False gives straight segments as degenerate cubics."""
    P = np.asarray(P, float)
    if smooth: return catmull_closed(P, tension)
    return [(P[i], P[i] + (P[(i + 1) % len(P)] - P[i]) / 3, P[i] + 2 * (P[(i + 1) % len(P)] - P[i]) / 3, P[(i + 1) % len(P)]) for i in range(len(P))]

def path_string(subpaths):
    """subpaths: list of segment lists (closed). Emits 'Mx y c... Z' per subpath, relative cubics, 1 decimal, with
    rounding error carried (each relative step is taken from the previously *rounded* point)."""
    out = []
    for segs in subpaths:
        p0 = np.round(segs[0][0], 1); cur = p0.copy()
        parts = ['M%s %s' % (fmt(p0[0]), fmt(p0[1]))]
        for k, (_, c1, c2, p1) in enumerate(segs):
            if k == len(segs) - 1: p1 = p0          # close exactly on the start point
            d1 = np.round(c1 - cur, 1); d2 = np.round(c2 - cur, 1); d3 = np.round(p1 - cur, 1)
            parts.append('c%s %s %s %s %s %s' % tuple(fmt(v) for v in (d1[0], d1[1], d2[0], d2[1], d3[0], d3[1])))
            cur = cur + d3
        parts.append('Z')
        out.append(''.join(parts))
    return ''.join(out)
