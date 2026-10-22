"""Shared painted-irregularity layer, applied by every recipe through `organic()` (targets: irregularity.json).

- outline wobble: outlines displaced along their outward normal by position-based noise (fine ~6 u, mid ~16 u, coarse
  ~45 u), so coincident edges of neighbouring shapes stay coincident;
- colour mottling: luminance-weighted value noise (correlation ~8 u, stronger in dark tones) plus a slight warm/cool
  hue drift, added to every colour field;
- tone regions that do not follow the silhouette: `inset()` = a noisy, uneven inset of a silhouette SDF;
- size/shape asymmetry: `vary()` lognormal factors with a given coefficient of variation;
- ground shadows: `shadow()` separate soft shapes in the ground layer, ground colour darkened with a mesh gradient."""
import json
import numpy as np
from common import EXT
from .geom import multi_path, Grid, sd_ellipse
from .paint import Noise, emit

LUMW = np.array([0.299, 0.587, 0.114])
_T = json.load(open(EXT / 'irregularity.json'))

# Outline wobble per layer (amplitudes in u): fine / mid / coarse. Calibrated so the 1 u turning-angle distribution of
# the output matches the live layer's (irr_compare.py).
WOBBLE = {'default': (0.35, 0.9, 1.6), 'frontTrees': (0.30, 0.8, 1.6), 'backTrees': (0.30, 0.8, 1.6),
          'pines': (0.36, 0.9, 1.2), 'bushes': (0.42, 1.0, 1.2), 'flowers': (0.30, 0.45, 0.5),
          'rocks': (0.36, 0.9, 1.4), 'pond': (0.35, 0.9, 1.6), 'meadow': (0.36, 1.0, 2.0), 'path': (0.2, 0.5, 1.0),
          'pathEdges': (0.25, 0.6, 1.0)}
_NOISE = {k: Noise(9000 + i) for i, k in enumerate(('f', 'm', 'c', 'mot1', 'mot2', 'hue', 'inset', 'sh'))}


def wobble(polys, layer, scale=1.0, seed=0):
    """Displace closed polylines along their outward normals by position-based noise."""
    af, am, ac = (a * scale for a in WOBBLE.get(layer, WOBBLE['default']))
    off = np.array([seed * 37.1, seed * 91.7])
    out = []
    for P in polys:
        P = np.asarray(P, float)
        # dense, even sampling so the fine wobble is represented
        from .geom import resample
        Q = resample(P, 0.8)
        if len(Q) < 6:
            out.append(P); continue
        a = np.sum(Q[:, 0] * np.roll(Q[:, 1], -1) - np.roll(Q[:, 0], -1) * Q[:, 1])
        t = np.roll(Q, -1, 0) - np.roll(Q, 1, 0)
        n = np.c_[t[:, 1], -t[:, 0]] / (np.hypot(*t.T)[:, None] + 1e-9)
        if a < 0:                                       # make n point outward (y-down, clockwise/ccw)
            n = -n
        X, Y = Q[:, 0] + off[0], Q[:, 1] + off[1]
        d = af * _NOISE['f'](X, Y, 5.0, 1) + am * _NOISE['m'](X, Y, 16.0, 1) + ac * _NOISE['c'](X, Y, 45.0, 1)
        out.append(Q + n * d[:, None])
    return out


def _amp(layer, tone):
    """Mottling amplitude (0..1 RGB units of luminance std) for a layer at a tone 0 (dark) .. 1 (light)."""
    m = _T['mottling'].get(layer) or _T['mottling']['bushes']
    dark, light = m['dark']['amp_lum_median'], m['light']['amp_lum_median']
    return (dark + (light - dark) * np.clip(tone, 0, 1)) / 255.0


def mottle(field, layer, strength=1.0, seed=0):
    """Wrap a colour field with painted mottling: value noise at ~8 u (two octaves), amplitude per tone from the live
    layer's measurements, plus a gentle warm/cool drift at ~30 u."""
    corr = (_T['mottling'].get(layer) or _T['mottling']['bushes'])['all']['corr_len_u_median']
    off = seed * 13.3

    def f(X, Y):
        C = field(X, Y)
        lum = C @ LUMW
        X2, Y2 = np.asarray(X) + off, np.asarray(Y) - off
        n = 0.75 * _NOISE['mot1'](X2, Y2, corr * 1.1, 2) + 0.45 * _NOISE['mot2'](X2, Y2, corr * 3.0, 1)
        a = _amp(layer, (lum - 0.35) / 0.5) * strength / 0.32           # noise std ~0.32 -> target std
        h = 0.012 * strength * _NOISE['hue'](X2, Y2, 30.0, 1)
        d = (n * a)[..., None] * np.ones(3) + h[..., None] * np.array([1.0, 0.4, -1.0])
        return np.clip(C + d, 0, 1)
    return f


def organic(layer, polys, field, cell=4.0, wob=1.0, mot=1.0, seed=0, step=2.4, force=None):
    """The one call every recipe uses to emit a shape: wobbled outline, mottled field, live mesh rule."""
    if not polys:
        return None
    P = wobble(polys, layer, wob, seed) if wob > 0 else polys
    f = mottle(field, layer, mot, seed) if mot > 0 else field
    return emit(layer, multi_path(P, step=step), f, cell=cell, force=force)


def inset(d, g, mean, var, corr=18.0, seed=0):
    """Silhouette SDF inset unevenly: boundary sits mean +- var u inside, varying along the outline (corr ~ u)."""
    n = _NOISE['inset'](g.X + seed * 7.7, g.Y - seed * 3.1, corr, 2)
    return d + np.clip(mean + var * n / 0.32, 0, None)


def vary(rng, n, cv):
    """n lognormal size factors with mean 1 and coefficient of variation cv."""
    s = np.sqrt(np.log(1 + cv * cv))
    return rng.lognormal(-s * s / 2, s, n)


def shadow(layer, ground, cx, cy, rx, ry, depth=0.16, seed=0, lobes=5, ang=0.0, skew=0.25):
    """Soft ground shadow as its own shape: an irregular lobed blob around (cx, cy); colour = ground(X, Y) darkened by
    `depth` (fraction of luminance) at the core, easing to ~15 % of that at the rim (a soft but visible painted edge,
    as the live shadows). `skew` pushes the darkest part toward the top (under the object)."""
    rng = np.random.default_rng(seed)
    g = Grid(cx - rx * 1.6, cy - ry * 1.6, cx + rx * 1.6, cy + ry * 1.6, res=max(1.0, 30.0 / max(rx, 1)))
    ds = [sd_ellipse(g.X, g.Y, cx, cy, rx, ry, ang)]
    for a in rng.uniform(0, 2 * np.pi, lobes):
        r = rng.uniform(0.35, 0.55)
        ds.append(sd_ellipse(g.X, g.Y, cx + np.cos(a) * rx * 0.7, cy + np.sin(a) * ry * 0.7, rx * r, ry * r * 1.2))
    from .geom import union
    d = union(ds, min(rx, ry) * 0.15)
    polys = g.contours(d, min_area=4)

    def f(X, Y):
        C = ground(X, Y)
        r = np.clip(np.hypot((X - cx) / rx, (Y - cy + skew * ry) / ry), 0, 1.6)
        k = depth * (0.15 + 0.85 * np.exp(-1.6 * r * r))
        return C * (1 - k[..., None]) + C * np.array([-0.02, 0.0, -0.04]) * k[..., None]
    return organic(layer, polys, f, wob=0.8, mot=0.6, seed=seed)
