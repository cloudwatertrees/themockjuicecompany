"""Colour fields and shape emission in the live art's fill format (flat / bilinear mesh, density rule from facts.json)."""
import common  # noqa: F401  (puts the forest-art renderer on sys.path)
import numpy as np
from art import parse_path, flatten, hex2rgb, rgb2hex
from pbart import PShape, tight_bounds, bilinear_dense


def hexes(*hs):
    return [hex2rgb(h) for h in hs]


def ramp(stops):
    """stops: [(t, 'RRGGBB'), ...] -> f(t array) -> (..., 3)."""
    ts = np.array([s[0] for s in stops], float)
    cs = np.array([hex2rgb(s[1]) for s in stops])
    def f(t):
        t = np.clip(np.asarray(t, float), ts[0], ts[-1])
        return np.stack([np.interp(t, ts, cs[:, k]) for k in range(3)], -1)
    return f


def mix(a, b, t):
    t = np.asarray(t, float)[..., None]
    return a * (1 - t) + b * t


class Noise:
    """Seeded smooth value noise (cosine-interpolated lattice), several octaves, roughly in [-1, 1]."""
    def __init__(self, seed, size=256):
        r = np.random.default_rng(seed)
        self.t = r.uniform(-1, 1, (size, size)); self.n = size
        self.off = r.uniform(0, size, 2)

    def _one(self, X, Y):
        X = X + self.off[0]; Y = Y + self.off[1]
        i, j = np.floor(X).astype(int), np.floor(Y).astype(int)
        fx, fy = X - i, Y - j
        fx = (1 - np.cos(fx * np.pi)) / 2; fy = (1 - np.cos(fy * np.pi)) / 2
        n = self.n; t = self.t
        a = t[j % n, i % n]; b = t[j % n, (i + 1) % n]; c = t[(j + 1) % n, i % n]; d = t[(j + 1) % n, (i + 1) % n]
        return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

    def __call__(self, X, Y, scale, octaves=2):
        out = 0.0; amp = 1.0; tot = 0.0; s = 1.0 / scale
        for o in range(octaves):
            out = out + amp * self._one(X * s, Y * s); tot += amp; amp *= 0.5; s *= 2.03
        return out / tot


def area(subs):
    a = 0.0
    for P in flatten(subs, 1.0, tol=0.2):
        a += 0.5 * abs(np.dot(P[:, 0], np.roll(P[:, 1], -1)) - np.dot(P[:, 1], np.roll(P[:, 0], -1)))
    return a


def _inside(subs, X, Y):
    inside = np.zeros(X.shape, bool)
    for P in flatten(subs, 1.0, tol=0.2):
        for (ax, ay), (bx, by) in zip(P, np.roll(P, -1, 0)):
            cond = ((ay > Y) != (by > Y)) & (X < ax + (Y - ay) * (bx - ax) / (by - ay + 1e-12))
            inside ^= cond
    return inside


def emit(layer, pathstr, field, cell=4.0, force=None):
    """PShape for `pathstr` filled from colour field `field(X, Y) -> (..., 3)` using the live density rule:
    flat under ~10 u2, 2x2 under ~100 u2, else ~`cell` u cells (4, or 8 for smooth shapes). `force`: 'flat'|'2x2'."""
    subs = parse_path(pathstr)
    b = tight_bounds(subs)
    box = (b[0] - 1, b[1] - 1, b[2] + 1, b[3] + 1)
    a = area(subs)
    kind = force or ('flat' if a < 10 else '2x2' if a < 100 else 'dense')
    if kind in ('flat', '2x2'):
        k = 24
        X, Y = np.meshgrid(np.linspace(b[0], b[2], k), np.linspace(b[1], b[3], k))
        m = _inside(subs, X, Y)
        if m.sum() < 3:
            X, Y, m = X, Y, np.ones_like(m)
        xs, ys = X[m], Y[m]
        C = field(xs, ys)
        if kind == 'flat':
            return PShape(layer, pathstr=pathstr, cols=C.mean(0)[None], nx=0, ny=0)
        Wt = bilinear_dense(box, 2, 2, xs, ys)
        cols = np.linalg.lstsq(Wt.T @ Wt + 1e-3 * np.eye(4), Wt.T @ C, rcond=None)[0]
        return PShape(layer, pathstr=pathstr, cols=np.clip(cols, 0, 1), nx=2, ny=2)
    bw, bh = box[2] - box[0], box[3] - box[1]
    nx, ny = max(int(round(bw / cell)) + 1, 2), max(int(round(bh / cell)) + 1, 2)
    X, Y = np.meshgrid(np.linspace(box[0], box[2], nx), np.linspace(box[1], box[3], ny))
    cols = np.clip(field(X, Y).reshape(-1, 3), 0, 1)
    return PShape(layer, pathstr=pathstr, cols=cols, nx=nx, ny=ny)


def flat(layer, pathstr, hexcol):
    return PShape(layer, pathstr=pathstr, cols=hex2rgb(hexcol)[None], nx=0, ny=0)
