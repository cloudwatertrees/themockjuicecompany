"""Old rooted tree (landmark): bespoke, no live equivalent. Built with the live construction rules:
- every tone region is a lighter (or darker) copy of its base piece, offset toward (or away from) the light and
  clipped to the base, so it shares the outer edge on the lit side;
- canopy = scalloped cloud lobes (the doorBush/hedge edge), dark under-canopy band, lit lobe caps;
- trunk + flared roots in the live log palette with lit-side copies, moss patches, soft ground shadow;
- all pieces through the shared irregularity layer (wobble, mottling)."""
import numpy as np
from .geom import Grid, sd_circle, sd_ellipse, sd_uneven_capsule, sd_poly, union, smin
from .paint import ramp, Noise
from .irregular import organic, vary, shadow
from .trees import light_side

CANOPY = ramp([(0.0, '35604F'), (0.2, '3F6E5A'), (0.4, '4F8A68'), (0.6, '6BA673'), (0.8, '8FC183'), (1.0, 'AED48F')])
BARK = ramp([(0.0, '5E3A2C'), (0.25, '754333'), (0.5, '9D6044'), (0.75, 'BB7852'), (1.0, 'D39463')])
MOSS = ramp([(0.0, '6F8F50'), (0.5, '8FAE62'), (1.0, 'B0C77E')])


def lit_copy(g, d, dx, dy, grow=0.0):
    """SDF of a copy of base `d` shifted by (dx, dy) u, clipped to the base: shares the base outline on the side the
    copy moved toward."""
    ix, iy = int(round(dx * g.res)), int(round(dy * g.res))
    big = float(d.max())
    sh = np.full_like(d, big)
    ys = slice(max(iy, 0), d.shape[0] + min(iy, 0)); yd = slice(max(-iy, 0), d.shape[0] + min(-iy, 0))
    xs = slice(max(ix, 0), d.shape[1] + min(ix, 0)); xd = slice(max(-ix, 0), d.shape[1] + min(-ix, 0))
    sh[ys, xs] = d[yd, xd]
    return np.maximum(d, sh - grow)


def old_tree(cx, base_y, ground, scale=1.0, seed=0):
    """Tree standing at (cx, base_y): trunk ~95 u wide at the canopy, flared roots spreading ~300 u, canopy ~420 x 330 u
    (x scale). Tone rule everywhere: lit piece = copy of the base moved toward the light by ~45 % of its size, clipped
    to the base, so the dark base remains as a crescent on the shade side."""
    rng = np.random.default_rng(seed)
    s = light_side(cx)                                   # +1: light from the right, -1: from the left
    k = scale
    out = []
    out.append(shadow('meadow', ground, cx - s * 25 * k, base_y + 2 * k, 210 * k, 40 * k, depth=0.24, seed=seed + 1, lobes=7))
    out.append(shadow('meadow', ground, cx - s * 12 * k, base_y - 4 * k, 130 * k, 22 * k, depth=0.16, seed=seed + 2, lobes=5))

    # ---------------- trunk and roots ----------------
    tw = 46 * k
    top_y = base_y - 235 * k
    g = Grid(cx - 230 * k, top_y - 20 * k, cx + 230 * k, base_y + 40 * k, res=2.0)
    ys = np.linspace(top_y, base_y - 10 * k, 40)
    flare = lambda y: tw * (1 + 1.1 * np.clip((y - (base_y - 95 * k)) / (85 * k), 0, 1) ** 2.2)
    lean = lambda y: 7 * k * np.sin((y - top_y) / (235 * k) * 2.0 + seed)
    P = np.vstack([np.c_[cx + flare(ys) + lean(ys), ys], np.c_[cx - flare(ys)[::-1] + lean(ys[::-1]), ys[::-1]]])
    trunk = sd_poly(g.X, g.Y, P)
    roots = []
    n = 5
    angs = np.array([-0.05, 0.55, 1.57, 2.6, np.pi + 0.05]) + rng.uniform(-0.12, 0.12, n)
    lens = vary(rng, n, 0.22) * np.array([125, 70, 30, 70, 125]) * k
    lens = lens * np.where(np.cos(angs) * s > 0.3, 0.45, 1.0)          # short on the clearing (path) side
    for a, ln in zip(angs, lens):
        dx = np.cos(a)
        bx = cx + dx * tw * 1.6; by = base_y - 14 * k
        ex = bx + dx * ln; ey = base_y + (4 + 10 * (1 - abs(dx))) * k + rng.uniform(-4, 6) * k
        mx, my = bx + dx * ln * 0.45, (by + ey) / 2 - 12 * k * abs(dx)
        r0 = 22 * k * rng.uniform(0.85, 1.1) * (0.8 + 0.2 * abs(dx))
        d = smin(sd_uneven_capsule(g.X, g.Y, bx, by, mx, my, r0, r0 * 0.6),
                 sd_uneven_capsule(g.X, g.Y, mx, my, ex, ey, r0 * 0.6, 8.5 * k), 5 * k)
        roots.append(d)
    wood = smin(trunk, union(roots, 8 * k), 14 * k)
    noise = Noise(seed + 9)

    def bark(X, Y):
        v = np.clip((Y - top_y) / (base_y - top_y), 0, 1)
        stripes = 0.05 * np.sin((X - cx) / (6.0 * k) + 2.5 * noise(X, Y, 28.0))
        return BARK(0.30 + 0.06 * v + stripes)
    out.append(organic('backTrees', g.contours(wood, min_area=10), bark, seed=seed + 3, step=2.0))
    lit = lit_copy(g, wood, s * 0.45 * tw, -6 * k)
    def litf(X, Y):
        stripes = 0.05 * np.sin((X - cx) / (6.0 * k) + 2.5 * noise(X, Y, 28.0))
        v = np.clip((Y - top_y) / (base_y - top_y), 0, 1)
        return BARK(0.58 + 0.10 * v + stripes)
    out.append(organic('backTrees', g.contours(lit, min_area=12), litf, seed=seed + 4))
    hi = lit_copy(g, lit, s * 0.5 * tw, -4 * k)          # brightest strip on the lit edge
    out.append(organic('backTrees', g.contours(hi, min_area=12), lambda X, Y: BARK(0.80 + 0.06 * noise(X, Y, 8.0)), seed=seed + 5))
    # under-canopy shade across the top of the trunk
    sh = np.maximum(trunk, g.Y - (top_y + 55 * k + 8 * k * np.sin((g.X - cx) / (12 * k))))
    out.append(organic('backTrees', g.contours(sh, min_area=12), lambda X, Y: BARK(0.14 + 0.10 * np.clip((Y - top_y) / (60 * k), 0, 1)), seed=seed + 6))
    for i in (1, 3):
        a = angs[i]
        m = np.maximum(roots[i] + 1.5 * k, sd_ellipse(g.X, g.Y, cx + np.cos(a) * (tw * 1.6 + lens[i] * 0.4), base_y - 26 * k,
                                                       26 * k, 11 * k) + 3 * noise(g.X, g.Y, 5.0))
        pp = g.contours(m, min_area=6)
        if pp:
            out.append(organic('backTrees', pp, lambda X, Y: MOSS(0.45 + 0.4 * noise(X, Y, 6.0)), seed=seed + 20 + i))

    # ---------------- canopy ----------------
    ccy = top_y - 85 * k
    rx, ry = 215 * k, 160 * k
    gc = Grid(cx - rx * 1.3, ccy - ry * 1.45, cx + rx * 1.3, ccy + ry * 1.3, res=1.6)
    rim = []
    m = 13
    for t in np.linspace(0, 2 * np.pi, m, endpoint=False) + rng.uniform(0, 0.5):
        rr = rng.uniform(0.85, 1.0)
        up = -np.sin(t)
        px = cx + np.cos(t) * rx * 0.8 * rr
        py = ccy + np.sin(t) * ry * (0.55 if up < 0 else 0.82) * rr
        rim.append((px, py, (62 if up > -0.3 else 46) * k * rng.uniform(0.85, 1.12)))
    base = union([sd_ellipse(gc.X, gc.Y, cx, ccy, rx * 0.82, ry * 0.68)] + [sd_circle(gc.X, gc.Y, *l) for l in rim], 3 * k)

    def cfield(X, Y):
        v = np.clip((Y - (ccy - ry)) / (ry * 1.9), 0, 1)
        return CANOPY(0.28 - 0.18 * v)
    out.append(organic('frontTrees', gc.contours(base, min_area=20), cfield, seed=seed + 30, cell=8.0, step=2.4))
    # cloud lobes, back (upper rows) to front (lower rows); each = mid base + lit copy (toward the light) + highlight
    clouds = [l for l in rim if l[1] < ccy + ry * 0.25]
    for i in range(7):
        t = rng.uniform(0, 2 * np.pi); rr = np.sqrt(rng.uniform(0.0, 0.5))
        clouds.append((cx + np.cos(t) * rx * rr * 0.8, ccy + np.sin(t) * ry * rr * 0.6 - 8 * k, 66 * k * rng.uniform(0.8, 1.1)))
    clouds.sort(key=lambda l: l[1])
    for j, l in enumerate(clouds):
        x0, y0, r = l
        cl = [l] + [(x0 + rng.uniform(-0.8, 0.8) * r, y0 + rng.uniform(0.0, 0.5) * r, r * rng.uniform(0.5, 0.7)) for _ in range(2)]
        d = np.maximum(union([sd_circle(gc.X, gc.Y, *c) for c in cl], 3 * k), base)
        depth = np.clip((y0 - (ccy - ry)) / (ry * 1.9), 0, 1)
        pp = gc.contours(d, min_area=40)
        if not pp:
            continue
        out.append(organic('frontTrees', pp, lambda X, Y, depth=depth: CANOPY(0.40 - 0.14 * depth), seed=seed + 40 + j, cell=8.0))
        L1 = lit_copy(gc, d, s * 0.30 * r * rng.uniform(0.8, 1.2), -0.42 * r * rng.uniform(0.8, 1.2))
        lp = gc.contours(L1, min_area=30)
        if lp:
            out.append(organic('frontTrees', lp, lambda X, Y, y0=y0, r=r, depth=depth:
                               CANOPY(0.66 - 0.12 * depth + 0.10 * np.clip((y0 - Y) / r, 0, 1)), seed=seed + 60 + j, cell=8.0))
        L2 = lit_copy(gc, L1, s * 0.22 * r, -0.30 * r)
        hp = gc.contours(L2, min_area=30)
        if hp and depth < 0.32:
            out.append(organic('frontTrees', hp, lambda X, Y, depth=depth: CANOPY(0.88 - 0.10 * depth), seed=seed + 80 + j, cell=8.0))
    return [o for o in out if o is not None]


def lit_copy_raw(g, d, dx, dy):
    """SDF `d` translated by (dx, dy) u on grid g (outside filled with the field maximum)."""
    ix, iy = int(round(dx * g.res)), int(round(dy * g.res))
    sh = np.full_like(d, float(d.max()))
    ys = slice(max(iy, 0), d.shape[0] + min(iy, 0)); yd = slice(max(-iy, 0), d.shape[0] + min(-iy, 0))
    xs = slice(max(ix, 0), d.shape[1] + min(ix, 0)); xd = slice(max(-ix, 0), d.shape[1] + min(-ix, 0))
    sh[ys, xs] = d[yd, xd]
    return sh
