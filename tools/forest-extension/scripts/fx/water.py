"""Shallow stream, built like the live pond: olive bank strip (thicker on the far/upper side), water mesh deep blue
under the far bank easing to light blue at the near side, light cyan band just inside the far edge (= water minus a
copy of itself moved down), pale ripple dashes along the flow; stones, lily pads and reeds come from live specimens."""
import numpy as np
from scipy.interpolate import CubicSpline
from .geom import Grid, sd_ellipse
from .paint import ramp, Noise
from .irregular import organic

WATER = ramp([(0.0, '4C9DCE'), (0.3, '57ABD8'), (0.6, '63BEE1'), (1.0, '78CBE6')])
RIM = ramp([(0.0, '76C6E4'), (1.0, '93D6EE')])
BANK = ramp([(0.0, '9FA05E'), (0.5, 'ABAA65'), (1.0, 'BDB97B')])
RIPPLE = ramp([(0.0, '8FD2EC'), (1.0, 'B4E2F2')])


class Stream:
    def __init__(self, knots, widths):
        """knots: [(x, y)] along the flow; widths: [(t 0..1, half-width u)]."""
        P = np.array(knots, float)
        d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
        self.len = d[-1]
        self.cx = CubicSpline(d, P[:, 0]); self.cy = CubicSpline(d, P[:, 1])
        tw = np.array(widths, float)
        self.hw = lambda s: np.interp(s / self.len, tw[:, 0], tw[:, 1])
        self.s = np.linspace(-40, self.len + 40, 900)
        self.pts = np.c_[self.cx(self.s), self.cy(self.s)]

    def sdf(self, g, grow=0.0):
        """Signed distance to the variable-width ribbon (negative inside), on grid g."""
        from scipy.spatial import cKDTree
        tree = cKDTree(self.pts)
        q = np.c_[g.X.ravel(), g.Y.ravel()]
        dist, idx = tree.query(q)
        w = self.hw(np.clip(self.s[idx], 0, self.len))
        return (dist - w - grow).reshape(g.X.shape), np.clip(self.s[idx], 0, self.len).reshape(g.X.shape)


def stream(st, box, seed=0, layer='pond'):
    """Water pieces for Stream `st` over the design box (x0, y0, x1, y1). Returns PShapes back to front."""
    rng = np.random.default_rng(seed)
    noise = Noise(seed + 5)
    g = Grid(*box, res=1.5)
    d, sp = st.sdf(g)
    out = []
    # bank: water grown, more on the far (upper) side: offset the grown copy upward
    from .oldtree import lit_copy_raw
    bank = np.minimum(d - 5.0, lit_copy_raw(g, d, 0, -6) - 4.0) + 1.6 * noise(g.X, g.Y, 9.0)
    out.append(organic(layer, g.contours(bank, min_area=20), lambda X, Y: BANK(0.5 + 0.35 * noise(X, Y, 14.0)), seed=seed + 1, wob=1.2))
    # water body: depth from the far (upper) edge: distance to the water region shifted up
    up = lit_copy_raw(g, d, 0, 14)                         # copy moved down 14 u: inside it = away from the far edge
    def wfield(X, Y):
        from scipy import ndimage as ndi
        u = (X - g.x0) * g.res; v = (Y - g.y0) * g.res
        dd = ndi.map_coordinates(up, [v.ravel(), u.ravel()], order=1, mode='nearest').reshape(np.shape(X))
        t = np.clip(0.55 - dd / 30.0, 0, 1)               # 0 deep under the far bank .. 1 light near side
        return WATER(0.15 + 0.75 * t + 0.08 * noise(X, Y, 20.0))
    out.append(organic(layer, g.contours(d, min_area=20), wfield, seed=seed + 2, wob=0.8, cell=4.0))
    # light band just inside the far edge
    rim = np.maximum(d, -lit_copy_raw(g, d, 0, 6.5))
    out.append(organic(layer, g.contours(rim, min_area=10), lambda X, Y: RIM(0.5 + 0.4 * noise(X, Y, 10.0)), seed=seed + 3, wob=0.5))
    # ripple dashes: short pale strokes along the flow
    for i in range(int(st.len / 55)):
        s0 = rng.uniform(0.05, 0.95) * st.len
        x, y = st.cx(s0), st.cy(s0)
        ang = np.arctan2(st.cy(s0, 1), st.cx(s0, 1))
        off = rng.uniform(-0.5, 0.5) * st.hw(s0)
        x += -np.sin(ang) * off; y += np.cos(ang) * off
        L = rng.uniform(4, 9)
        gg = Grid(x - L - 3, y - L - 3, x + L + 3, y + L + 3, res=6.0)
        dd = sd_ellipse(gg.X, gg.Y, x, y, L, rng.uniform(0.9, 1.5), ang)
        out.append(organic(layer, gg.contours(dd, min_area=1), lambda X, Y: RIPPLE(0.5) * np.ones(np.shape(X) + (3,)),
                           seed=seed + 10 + i, wob=0.2, force='flat'))
    return [o for o in out if o is not None]
