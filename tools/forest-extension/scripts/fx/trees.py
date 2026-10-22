"""Bell-tier conifers (frontTrees/backTrees recipe): stacked bell tiers with scalloped hems, lit toward the clearing."""
import numpy as np
from .geom import Grid, sd_circle, sd_ellipse, sd_poly, union, smin, multi_path
from .paint import ramp, emit, Noise, mix

# Palette sampled from the live frontTrees layer (dark -> light).
TIER = ramp([(0.0, '3A6A5A'), (0.2, '467F69'), (0.4, '5B9972'), (0.6, '7BB77F'), (0.8, '9CCB89'), (1.0, 'B4D592')])
CLEARING_X = 470.0


def light_side(cx):
    """+1 if the light falls from the right (element left of the clearing), -1 from the left."""
    return 1.0 if cx < CLEARING_X else -1.0


class Tier:
    """One bell tier: dome (radius rt), near-straight neck, concave flare, and a hem of n overlapping round lobes
    (crisp notches; outer lobes slightly larger so the tips round off past the flare). Proportions measured on the
    live art: top tier H ~ 1.9 W, rt ~ 0.45 W, flare over the lower ~60 %, scallop depth ~0.27 of the lobe pitch."""
    def __init__(self, cx, ty, W, rng, H=None, nlobes=None, neck=0.22, rt=None, p=None):
        self.cx, self.ty, self.W = cx, ty, W
        self.rt = rt if rt is not None else W * rng.uniform(0.42, 0.48)
        self.H = H if H is not None else W * rng.uniform(1.8, 2.0)
        self.hem = ty + self.H                            # bottom of the lobes
        self.neck = neck
        self.p = p if p is not None else rng.uniform(1.2, 1.35)
        self.n = nlobes or (4 if W > 45 else 3)
        self.asym = rng.uniform(-0.06, 0.06)                # right flank wider (+) or narrower (-)
        pitch = 2 * W / (self.n + 0.35)
        self.r = r = pitch * 0.56
        self.lobes = []
        xs = np.linspace(cx - W + r, cx + W - r, self.n)
        for i, x in enumerate(xs):
            outer = i in (0, self.n - 1)
            rr = r * rng.uniform(0.96, 1.04)
            ry = rr * (0.88 if outer else 0.85)
            cy = self.hem - ry - (ry * 0.18 if outer else 0) + rng.uniform(-0.5, 0.5)
            ang = (-0.25 if i == 0 else 0.25) if outer else rng.uniform(-0.08, 0.08)
            self.lobes.append((x + rng.uniform(-0.8, 0.8), cy, rr, ry, ang))
        self.body_bottom = self.hem - r * 0.85 * 1.3

    def half_width(self, y):
        yd = self.ty + self.rt
        t = np.clip((y - yd) / (self.body_bottom - yd), 0, 1)
        f = np.clip((t - self.neck) / (1 - self.neck), 0, 1)
        w_end = self.W - self.r * 0.3
        return self.rt * (1 + 0.06 * t) + (w_end - self.rt * 1.06) * f ** self.p

    def sdf(self, X, Y):
        yd = self.ty + self.rt
        ys = np.linspace(yd, self.body_bottom, 48)
        w = self.half_width(ys)
        a = self.asym * np.linspace(0, 1, len(ys)) ** 1.5
        P = np.vstack([np.c_[self.cx + w * (1 + a), ys], np.c_[self.cx - w * (1 - a), ys][::-1]])
        body = smin(sd_poly(X, Y, P), sd_circle(X, Y, self.cx, yd, self.rt), 2.0)
        lob = union([sd_ellipse(X, Y, x, y, rx, ry, a) for x, y, rx, ry, a in self.lobes], 0.6)
        return smin(body, lob, 1.5)


def bell_tree(cx, top, W, tiers=3, seed=0, layer='frontTrees', side=None):
    """W ~ hem half-width of the lowest tier. Returns PShapes back to front (lowest tier first)."""
    rng = np.random.default_rng(seed)
    noise = Noise(seed + 101)
    s = light_side(cx) if side is None else side
    ts = []
    y = top
    for i in range(tiers):                               # spec order: top tier first
        f = i / max(tiers - 1, 1)
        w = W * (0.85 + 0.15 * f) * rng.uniform(0.96, 1.04) if i else W * rng.uniform(0.86, 0.92)
        if i == 0:
            t = Tier(cx, y, w, rng)
        else:                                            # lower tiers: wide shoulders hidden under the tier above
            t = Tier(cx + rng.uniform(-3, 3), y, w, rng, H=w * rng.uniform(1.45, 1.55), neck=0.05, rt=w * 0.5, p=1.25)
        ts.append(t)
        nw = W * (0.85 + 0.15 * (i + 1) / max(tiers - 1, 1))
        y = t.hem + nw * rng.uniform(0.72, 0.8) - nw * 1.5      # next tier's hem ~0.75 W lower
    g = Grid(cx - W * 1.5, top - 4, cx + W * 1.5, ts[-1].hem + W * 0.4, res=3.0)
    shapes = []
    for i in reversed(range(tiers)):
        t = ts[i]
        above = ts[i - 1] if i > 0 else None
        d = t.sdf(g.X, g.Y)
        ph = rng.uniform(0, 6)

        def bfun(Y, t=t, ph=ph):                           # dark/lit boundary x(y): slightly on the dark side, wavy
            hw = np.maximum(t.half_width(Y), 1)
            return t.cx + s * hw * (-0.10 + 0.09 * np.sin((Y - t.ty) / t.H * 4.5 + ph))

        def under(Y, above=above):                         # shade just below the hem of the tier above
            if above is None:
                return 0.0
            return np.exp(-np.clip(Y - above.hem + 5, 0, None) / 16.0)

        def body(X, Y, t=t, bfun=bfun, under=under):
            e = s * (X - bfun(Y))                          # <0 on the dark side
            hw = np.maximum(t.half_width(Y), 1)
            v = np.clip((Y - t.ty) / t.H, 0, 1.1)
            tt = 0.46 + 0.20 * np.clip(e / hw, -1, 0.3) - 0.04 * v - 0.30 * under(Y)
            return TIER(tt + 0.035 * noise(X, Y, 8.0))
        shapes.append(emit(layer, multi_path(g.contours(d)), body))
        lit = np.maximum(d, s * (bfun(g.Y) - g.X))
        if above is not None:
            lit = np.maximum(lit, above.hem - 3 - g.Y)
        lp = g.contours(lit, min_area=30)
        if lp:
            def lfield(X, Y, t=t, bfun=bfun, under=under):
                e = s * (X - bfun(Y))
                hw = np.maximum(t.half_width(Y), 1)
                v = np.clip((Y - t.ty) / t.H, 0, 1.1)
                k = np.clip(e / 14.0, 0, 1); k = k * k * (3 - 2 * k)
                tt = 0.50 + 0.46 * k - 0.08 * v - 0.30 * under(Y) * (1 - 0.3 * k)
                return TIER(tt + 0.03 * noise(X, Y, 7.0))
            shapes.append(emit(layer, multi_path(lp), lfield))
    return shapes
