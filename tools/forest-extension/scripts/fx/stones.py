"""Rocks (faceted lilac-grey boulders), smooth stream stones and path pebbles."""
import numpy as np
from .geom import Grid, sd_ellipse, sd_poly, union, smin, multi_path
from .paint import ramp, emit, Noise
from .trees import light_side

# Palette sampled from the live rocks layer (dark -> light).
ROCK = ramp([(0.0, '6E6E86'), (0.3, '8B89A0'), (0.55, '9E9BB0'), (0.8, 'B5B1C0'), (1.0, 'C9C5D0')])
MOSS = ramp([(0.0, '7E9E5C'), (1.0, 'A9C27A')])
PEBBLE = ramp([(0.0, 'D9B98F'), (0.5, 'EBD3AE'), (1.0, 'F3DFBF')])


def rock_sdf(X, Y, cx, by, w, h, rng):
    """Boulder silhouette: domed top, widest low down, rounded base sitting at y = by."""
    top = sd_ellipse(X, Y, cx + rng.uniform(-0.05, 0.05) * w, by - h * 0.56, w * 0.44, h * 0.56)
    base = sd_ellipse(X, Y, cx, by - h * 0.28, w * 0.5, h * 0.28)
    return smin(top, base, w * 0.10)


def rock(cx, by, w, h, seed=0, layer='rocks', moss=False):
    """Painted facets like the live boulders: a large light top face, a dark left face, a mid front face and a
    narrow darker right face; soft gradients inside each face; slightly angular facet edges."""
    rng = np.random.default_rng(seed)
    noise = Noise(seed + 11)
    g = Grid(cx - w * 0.7, by - h * 1.2, cx + w * 0.7, by + 2, res=max(3.0, 120.0 / w))
    d = rock_sdf(g.X, g.Y, cx, by, w, h, rng)
    out = []
    v = lambda Y: np.clip((by - Y) / h, 0, 1)
    out.append(emit(layer, multi_path(g.contours(d)), lambda X, Y: ROCK(0.56 + 0.10 * v(Y) + 0.03 * noise(X, Y, 6.0))))
    jag = lambda Y, k: 0.035 * w * np.sign(np.sin((Y - by) / h * k + seed)) * np.abs(np.sin((Y - by) / h * k * 1.7 + seed))
    xl = cx - w * rng.uniform(0.12, 0.2) + (g.Y - by + h) / h * w * 0.06 + jag(g.Y, 9)
    dp = g.contours(np.maximum(d, g.X - xl), min_area=8)
    if dp:
        out.append(emit(layer, multi_path(dp), lambda X, Y: ROCK(0.30 + 0.12 * v(Y) + 0.03 * noise(X, Y, 5.0))))
    xr = cx + w * rng.uniform(0.28, 0.34) + jag(g.Y, 7)
    rp = g.contours(np.maximum(d, xr - g.X), min_area=8)
    if rp:
        out.append(emit(layer, multi_path(rp), lambda X, Y: ROCK(0.40 + 0.10 * v(Y) + 0.03 * noise(X, Y, 5.0))))
    yt = by - h * rng.uniform(0.55, 0.62) - (g.X - cx) * 0.12 + 0.04 * h * np.sin((g.X - cx) / w * 9 + seed)
    tp = g.contours(np.maximum(d, g.Y - yt), min_area=8)
    if tp:
        out.append(emit(layer, multi_path(tp), lambda X, Y: ROCK(0.80 + 0.12 * np.clip((by - h * 0.6 - Y) / (h * 0.4), 0, 1) + 0.03 * noise(X, Y, 5.0))))
    if moss:
        mp = np.maximum(d + 1.0, sd_ellipse(g.X, g.Y, cx + w * 0.05, by - h * 0.95, w * 0.2, h * 0.09) + 2 * noise(g.X, g.Y, 3.0))
        mpp = g.contours(mp, min_area=4)
        if mpp:
            out.append(emit(layer, multi_path(mpp), lambda X, Y: MOSS(0.5 + 0.3 * noise(X, Y, 4.0))))
    return out


def pebble(cx, cy, rx, ry, ang=0.0, seed=0, layer='path', palette=PEBBLE):
    """Flat path pebble: soft oval, darker rim at the bottom, paler top (as the live path pebbles)."""
    rng = np.random.default_rng(seed)
    g = Grid(cx - rx * 1.3, cy - ry * 1.3, cx + rx * 1.3, cy + ry * 1.3, res=max(4.0, 40.0 / rx))
    noise = Noise(seed + 5)
    d = sd_ellipse(g.X, g.Y, cx, cy, rx, ry, ang) + 0.6 * noise(g.X, g.Y, max(rx, 3) * 0.7)
    out = [emit(layer, multi_path(g.contours(d)), lambda X, Y: palette(0.25 + 0.2 * np.clip((cy - Y) / ry, -1, 1)))]
    # paler top inset
    d2 = sd_ellipse(g.X, g.Y, cx - rx * 0.03, cy - ry * 0.12, rx * 0.86, ry * 0.78, ang) + 0.5 * noise(g.X, g.Y, max(rx, 3) * 0.6)
    p2 = g.contours(d2, min_area=1)
    if p2:
        out.append(emit(layer, multi_path(p2), lambda X, Y: palette(0.55 + 0.15 * np.clip((cy - Y) / ry, -1, 1))))
    return out
