"""Leafy plants built from rounded leaflets: fern-pine (pines layer), ferns and leaf clumps (bushes layer)."""
import numpy as np
from .geom import Grid, sd_ellipse, sd_uneven_capsule, union, smin, multi_path
from .paint import ramp, emit, Noise, mix
from .trees import light_side
from .irregular import organic, vary, inset

# Palettes sampled from the live pines / bushes layers (dark -> light).
PINE = ramp([(0.0, '3C735E'), (0.25, '498663'), (0.5, '70AD72'), (0.75, '94C47F'), (1.0, 'B2D592')])
LEAF = ramp([(0.0, '426F55'), (0.25, '598A60'), (0.5, '70A773'), (0.75, '82C289'), (1.0, 'A6D49A')])
HALO = ramp([(0.0, 'E4DEA1'), (1.0, 'F2EAC0')])


def finger(X, Y, bx, by, ang, length, width, tip=1.0):
    """Leaflet from (bx, by) pointing at `ang` (radians, 0 = +x, y down): widest past its middle, rounded tip."""
    c, s = np.cos(ang), np.sin(ang)
    m = 0.55
    body = sd_ellipse(X, Y, bx + c * length * m, by + s * length * m, length * 0.47, width * 0.5, ang)
    rr = width * 0.40 * tip                               # blunt, rounded tip
    t = length - rr * 1.05
    return np.minimum(body, np.hypot(X - bx - c * t, Y - by - s * t) - rr)


def rosette(X, Y, cx, cy, fingers, core=None, k=1.6):
    """Union of fingers [(ang, length, width)] radiating from (cx, cy), plus an optional core ellipse (rx, ry)."""
    ds = [finger(X, Y, cx, cy, a, L, w) for a, L, w in fingers]
    if core:
        ds.append(sd_ellipse(X, Y, cx, cy, core[0], core[1]))
    return union(ds, k)


def fan(rng, n, a0, a1, L, w, jitter=0.08, lvar=0.12):
    """n fingers spread over angles a0..a1 (radians), lengths peaking in the middle of the fan."""
    out = []
    for i, a in enumerate(np.linspace(a0, a1, n)):
        mid = 1 - abs((i / max(n - 1, 1)) - 0.5) * 0.5
        out.append((a + rng.uniform(-jitter, jitter), L * mid * rng.uniform(1 - lvar, 1 + lvar), w * rng.uniform(0.9, 1.1)))
    return out


def fern_pine(cx, top, W, tiers=3, seed=0, layer='pines', halo=True, ground=None):
    """Stacked leaf-rosette conifer like the live pines (Stage-1 geometry) through the shared irregularity layer:
    per tier one rosette of blunt oval leaflets on an elliptical reach profile (uneven lengths, fan rotated, left/right
    reach differ) plus front hem lobes; radial shading with a dark core under the tier above and lighter front lobes;
    wobbled outlines, mottled fields; pale egg halo with the soft shadow under the tree painted into it."""
    from .irregular import shadow
    rng = np.random.default_rng(seed)
    s = light_side(cx)
    H = W * 2.5
    lean = rng.uniform(-0.05, 0.05)
    g = Grid(cx - W * 1.5, top - 8, cx + W * 1.5, top + H + W * 0.5, res=4.0)
    prof = {3: [(0.42, 0.95, 0.62), (0.66, 0.72, 1.0), (0.84, 0.5, 1.0)],
            4: [(0.36, 0.85, 0.52), (0.56, 0.7, 0.8), (0.72, 0.6, 1.0), (0.87, 0.45, 1.0)]}[tiers]
    specs = []
    for i, (fy, lv, lh) in enumerate(prof):
        cy = top + H * fy
        tcx = cx + lean * (cy - top - H) + rng.uniform(-0.03, 0.03) * W
        Lv, Lh = lv * W, lh * W
        Lr, Ll = Lh * rng.uniform(0.94, 1.06), Lh * rng.uniform(0.94, 1.06)
        n = 7 + 2 * (i > 0)
        rot = rng.uniform(-0.08, 0.08)
        amax = 1.45 if i == 0 else 1.22
        lens = vary(rng, n, 0.11)
        fingers = []
        for k, th in enumerate(np.linspace(-amax, amax, n)):
            th = th + rot + rng.uniform(-0.06, 0.06)
            lh_ = Lr if th > 0 else Ll
            r = 1 / np.sqrt((np.cos(th) / Lv) ** 2 + (np.sin(th) / lh_) ** 2) * lens[k]
            fingers.append((-np.pi / 2 + th, r, min(r * 0.40, W * 0.27) * rng.uniform(0.9, 1.08)))
        m = 3 if i == 0 else 4
        fl = vary(rng, m, 0.15)
        for j, a in enumerate(np.linspace(np.pi / 2 - 0.95, np.pi / 2 + 0.95, m)):
            fingers.append((a + rot + rng.uniform(-0.08, 0.08), Lh * 0.46 * fl[j], Lh * rng.uniform(0.34, 0.40) * fl[j]))
        specs.append(dict(cx=tcx, cy=cy, L=(Lv + Lh) / 2, Lh=Lh, fingers=fingers))
    shapes = []
    if halo:
        hy = top + H * 0.62
        hd = sd_ellipse(g.X, g.Y, cx, hy, W * 1.36, H * 0.6)
        def hf(X, Y):
            r = np.hypot((X - cx) / (W * 1.36), (Y - hy) / (H * 0.6))
            c = HALO(np.clip(1.1 - r * 0.9, 0, 1))
            sh = np.exp(-(((X - cx) / (W * 0.95)) ** 2 + ((Y - top - H * 0.93) / (W * 0.33)) ** 2))
            return c * (1 - 0.15 * sh[..., None])
        shapes.append(organic(layer, g.contours(hd), hf, seed=seed + 50, wob=2.0))
    elif ground is not None:
        shapes.append(shadow(layer, ground, cx, top + H * 0.93, W * 0.95, W * 0.32, depth=0.2, seed=seed + 60))
    for i in reversed(range(tiers)):
        t = specs[i]
        above = specs[i - 1] if i > 0 else None
        d = rosette(g.X, g.Y, t['cx'], t['cy'], t['fingers'], core=(t['Lh'] * 0.62, t['Lh'] * 0.36), k=0.4)

        def field(X, Y, t=t, above=above):
            r = np.clip(np.hypot(X - t['cx'], Y - t['cy']) / (t['L'] * 1.05), 0, 1.2)
            side = np.clip(s * (X - t['cx']) / (t['L'] * 1.1), -1, 1)
            front = np.clip((Y - t['cy']) / (t['Lh'] * 0.42), 0, 1)
            v = 0.38 + 0.42 * r ** 1.2 + 0.13 * side + 0.20 * front
            if above is not None:
                dd = np.hypot((X - above['cx']) / above['L'], (Y - above['cy'] - above['L'] * 0.25) / (above['L'] * 0.7))
                v = v - 0.32 * np.exp(-dd ** 2 * 1.4)
            return PINE(v)
        shapes.append(organic(layer, g.contours(d), field, seed=seed + i))
    return [x for x in shapes if x is not None]


# ---- flowers -------------------------------------------------------------------------------------------------
PETALS = {
    'white': ramp([(0.0, 'DCDDB8'), (0.5, 'F3EED2'), (1.0, 'FCF8E6')]),
    'lilac': ramp([(0.0, 'A57CC0'), (0.5, 'C995E0'), (1.0, 'DDB2F0')]),
    'yellow': ramp([(0.0, 'E7BE3A'), (0.5, 'FAD94F'), (1.0, 'FDEB86')]),
}
FULL = {'white': (0.31, 0.70), 'lilac': (0.37, 0.64), 'yellow': (0.33, 0.68)}   # petal tip radius, tip distance (x R)
CENTRES = {'white': ('FFE163', 'F2B93A'), 'lilac': ('FFD966', 'F0B23C'), 'yellow': ('FFB54A', 'EE8F2E')}


def flower(cx, cy, R, kind='white', seed=0, layer='flowers'):
    """Five rounded petals (one shape, uneven sizes and spacing, paler at the tips and on top) and a yellow centre lit
    from above, set slightly off-centre."""
    rng = np.random.default_rng(seed)
    g = Grid(cx - R * 1.4, cy - R * 1.4, cx + R * 1.4, cy + R * 1.4, res=max(6.0, 40.0 / R))
    rot = rng.uniform(0, 2 * np.pi / 5)
    sizes = vary(rng, 5, 0.14)
    ds = [sd_ellipse(g.X, g.Y, cx, cy, R * 0.36, R * 0.35, rng.uniform(0, 3))]
    for k in range(5):
        a = rot + k * 2 * np.pi / 5 + rng.uniform(-0.12, 0.12)
        rt = R * FULL[kind][0] * sizes[k]                 # spoon petal: narrow base, round tip
        tip = R * (FULL[kind][1] + 0.06 * (sizes[k] - 1))
        ds.append(sd_uneven_capsule(g.X, g.Y, cx + np.cos(a) * R * 0.15, cy + np.sin(a) * R * 0.15,
                                    cx + np.cos(a) * tip, cy + np.sin(a) * tip, R * 0.17, rt))
    d = union(ds, R * 0.04)
    P = PETALS[kind]
    ox, oy = rng.uniform(-0.06, 0.06, 2) * R

    def pf(X, Y):
        r = np.clip(np.hypot(X - cx - ox, Y - cy - oy) / R, 0, 1)
        return P(0.32 + 0.58 * r - 0.16 * np.clip((Y - cy) / R, -1, 1))
    out = [organic(layer, g.contours(d), pf, seed=seed)]
    rc = R * rng.uniform(0.29, 0.34)
    dc = sd_ellipse(g.X, g.Y, cx + ox, cy + oy, rc, rc * rng.uniform(0.88, 0.98), rng.uniform(0, 3))
    c0, c1 = (np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)]) / 255 for h in CENTRES[kind])

    def cf(X, Y):
        t = np.clip((Y - cy - oy + rc) / (2 * rc), 0, 1)[..., None]
        return c0 * (1 - t) + c1 * t
    out.append(organic(layer, g.contours(dc), cf, seed=seed + 1, wob=0.6, mot=0.5, force='2x2' if rc < 6 else None))
    return [o for o in out if o is not None]


# ---- lobed leaves and leaf clumps (bushes layer) -------------------------------------------------------------
def palm_leaf(X, Y, bx, by, ang, size, lobes, rng):
    """Palmate leaf: `lobes` rounded leaflets fanned around `ang` from a small base (same build as a pine tier)."""
    spread = 0.55 + 0.12 * lobes
    fingers = []
    for k, a in enumerate(np.linspace(-spread, spread, lobes)):
        mid = 1 - abs(k / (lobes - 1) - 0.5) * 0.7
        L = size * mid * rng.uniform(0.9, 1.08)
        fingers.append((ang + a + rng.uniform(-0.07, 0.07), L, L * rng.uniform(0.30, 0.36)))
    return rosette(X, Y, bx, by, fingers, core=(size * 0.18, size * 0.15), k=size * 0.03)


FRONT = ramp([(0.0, '6F9A55'), (0.5, '92BC68'), (1.0, 'B2CF7E')])


def leaf_clump(cx, cy, R, seed=0, layer='bushes', n=None, palette=LEAF, front=3):
    """Loose mound of palmate leaves radiating from a low centre: back leaves fan upward (darker), side leaves lower,
    `front` small yellow-green leaves hang forward (lighter). Each leaf is its own shape, back to front; shading is
    darker at each leaf's base, lighter at its tips and on the side facing the light."""
    rng = np.random.default_rng(seed)
    noise = Noise(seed + 3)
    s = light_side(cx)
    n = n or 7
    g = Grid(cx - R * 1.5, cy - R * 1.4, cx + R * 1.5, cy + R * 1.0, res=3.0)
    leaves = []
    for k, a in enumerate(np.linspace(np.pi + 0.25, 2 * np.pi - 0.25, n)):
        a = a + rng.uniform(-0.12, 0.12)
        up = -np.sin(a)                                   # 1 = pointing straight up
        size = R * rng.uniform(0.85, 1.0) * (0.75 + 0.3 * up)
        leaves.append((0.2 * (1 - up) + rng.uniform(0, 0.25), cx + np.cos(a) * R * 0.12, cy + rng.uniform(-2, 2), a, size, palette))
    for k, a in enumerate(np.linspace(np.pi / 2 - 0.9, np.pi / 2 + 0.9, front)):
        size = R * rng.uniform(0.5, 0.62)
        leaves.append((1.0 + rng.uniform(0, 0.2), cx + np.cos(a) * R * 0.2, cy + R * 0.05, a + rng.uniform(-0.15, 0.15), size, FRONT))
    leaves.sort(key=lambda t: t[0])
    out = []
    ds = [palm_leaf(g.X, g.Y, bx, by, ang, size, int(rng.integers(5, 7)), rng) for _, bx, by, ang, size, _ in leaves]
    # dark inner mass behind the leaves: the gaps between leaves read as shade, not ground
    core = np.maximum(union(ds[:len(ds) - front], 0) + R * 0.10, sd_ellipse(g.X, g.Y, cx, cy - R * 0.25, R * 0.75, R * 0.6))
    cp = g.contours(core, min_area=20)
    if cp:
        out.append(emit(layer, multi_path(cp), lambda X, Y: palette(0.06 + 0.10 * np.clip((cy - Y) / R, 0, 1) + 0.04 * noise(X, Y, 6.0))))
    for i, (depth, bx, by, ang, size, pal) in enumerate(leaves):
        d = ds[i]
        tone = (0.16 + 0.34 * min(depth, 1.0) + rng.uniform(-0.08, 0.08)) if pal is palette else 0.30 + rng.uniform(-0.1, 0.1)

        def f(X, Y, bx=bx, by=by, size=size, tone=tone, pal=pal):
            r = np.clip(np.hypot(X - bx, Y - by) / size, 0, 1)
            side = np.clip(s * (X - cx) / R, -1, 1)
            return pal(tone + 0.38 * r ** 1.4 + 0.10 * side + 0.05 * noise(X, Y, 5.0))
        polys = g.contours(d)
        if polys:
            out.append(emit(layer, multi_path(polys), f))
    return out
