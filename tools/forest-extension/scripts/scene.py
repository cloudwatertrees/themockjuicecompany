"""The extension scene: composition, path, ground, seam caps and all elements, in extension space (937 x 1678,
y = 0 at the seam). `build()` returns the shapes back to front per layer. Deterministic: every random draw is seeded."""
import numpy as np
from common import load_live_layers, H, W
from art import hex2rgb
from fx.geom import poly_path, multi_path, Grid
from fx.paint import emit, ramp, Noise, mix
from fx.pathgen import PathModel, PathEdges
from fx.ground import Buffer, MEADOW, seam_profile, seam_blend
from fx import seam as S
from fx.stones import pebble, PEBBLE

SEED = 20261014


def NOFLOWER(order, s, kind):
    from fx.composites import is_flower_piece
    c = s.cols.mean(0)
    size = max(s.box[2] - s.box[0], s.box[3] - s.box[1])
    pale = c.min() > 0.70 and size < 110
    grey = c.max() - c.min() < 0.07 and size < 60
    return not is_flower_piece(s) and s.layer != 'flowers' and not pale and not grey
BLEED = 5.0                                          # the live art bleeds 5 u past the canvas; so does the extension

# ---- path design -----------------------------------------------------------------------------------------------
CENTRE = [(120, 470), (250, 405), (400, 340), (520, 318), (650, 345), (800, 420), (950, 510), (1100, 575),
          (1250, 585), (1400, 545), (1550, 485), (1700, 450), (1800, 440)]
HALF = [(200, 140), (500, 135), (800, 138), (1100, 142), (1400, 140), (1700, 138), (1800, 138)]
# band runs on the outer side of each bend: (start, full, end of full, end, side +1 right / -1 left)
BANDS = [(-400, -300, 120, 290, +1), (200, 360, 790, 950, -1), (850, 1000, 1400, 1550, +1)]
BAND_W = [(-100, 74.6), (0, 74.6), (300, 72), (700, 78), (1100, 74), (1500, 76), (1900, 74)]

PATH = ramp([(0.0, 'E9D3AC'), (0.35, 'F3DFBE'), (0.6, 'F6E4C3'), (0.8, 'F7E8CC'), (1.0, 'F9EBD2')])
BAND = ramp([(0.0, '94684B'), (0.4, 'A97A5C'), (0.7, 'B08062'), (1.0, 'BC8D6D')])
COBBLE = ramp([(0.0, 'B88A69'), (0.5, 'C49874'), (1.0, 'CFA582')])
RIM = 'EFE3B4'


def path_model():
    return PathModel(CENTRE, HALF, BANDS, BAND_W)


def build_path(pe, rng):
    out = {'path': [], 'pathEdges': []}
    noise = Noise(SEED + 1)
    prof = seam_profile()
    y0, y1 = -8.0, H + BLEED
    # surface: cream, slightly darker shoulder toward the band side, mottled
    clean = S.clean_profile(prof, [(368.5, 553.5), (608, 659.5)])

    def surface(X, Y):
        L = pe.at('left', Y); R = pe.at('right', Y)
        rb = pe.at('rbw', Y); lb = pe.at('lbw', Y)
        dl = X - L; dr = R - X
        t = 0.82 + 0.05 * noise(X, Y, 14.0) + 0.025 * noise(X, Y, 4.0)
        t = t - 0.20 * np.exp(-dr / 9.0) * np.clip(rb / 30, 0, 1) - 0.20 * np.exp(-dl / 9.0) * np.clip(lb / 30, 0, 1)
        t = t - 0.06 * np.exp(-dl / 6.0) * (1 - np.clip(lb / 30, 0, 1)) - 0.06 * np.exp(-dr / 6.0) * (1 - np.clip(rb / 30, 0, 1))
        return PATH(t)
    poly = pe.polygon(pe.left, pe.right, y0, y1)
    out['path'].append(emit('path', poly_path(poly, 3.0), seam_blend(surface, 60, clean)))
    # pale rim on edges without a band
    for edge, side in (('left', -1), ('right', +1)):
        e = getattr(pe, edge)
        bw = pe.lbw if side < 0 else pe.rbw
        m = (bw < 0.5) & (pe.y >= y0) & (pe.y <= y1)
        if not m.any():
            continue
        idx = np.where(m)[0]
        for run in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
            if len(run) < 6:
                continue
            ys = pe.y[run]; xe = e[run]
            a = np.c_[xe + side * 2.2, ys]; b = np.c_[xe - side * 0.3, ys]
            out['path'].append(emit('path', poly_path(np.vstack([a, b[::-1]]), 3.0, adaptive=False),
                                    lambda X, Y: hex2rgb(RIM) + 0.01 * noise(X, Y, 5.0)[..., None], cell=8.0))
    # brown band(s)
    for side, ain, aout, bw in ((+1, pe.rband_in, pe.rband_out, pe.rbw), (-1, pe.lband_in, pe.lband_out, pe.lbw)):
        m = (bw > 0.05) & (pe.y >= y0) & (pe.y <= y1)
        if not m.any():
            continue
        idx = np.where(m)[0]
        bclean = S.clean_profile(prof, [(661.5, 671.5), (680.5, 734.5)])
        for run in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
            ys = pe.y[run]
            A = np.c_[ain[run], ys]; B = np.c_[aout[run], ys]
            def bfield(X, Y, ain=ain, side=side):
                inner = np.abs(X - pe.at('rband_in' if side > 0 else 'lband_in', Y))
                t = 0.66 + 0.05 * noise(X, Y, 10.0) + 0.04 * noise(X, Y, 3.5) - 0.08 * np.exp(-inner / 5.0)
                return BAND(t)
            out['pathEdges'].append(emit('pathEdges', poly_path(np.vstack([A, B[::-1]]), 2.5),
                                         seam_blend(bfield, 50, bclean)))
            # thin pale line between cream and band (under the cream edge, filling the 1.2 u gap)
            k = np.clip(bw[run] / 20, 0, 1)
            a2 = np.c_[ain[run] - side * 1.6, ys]; b2 = np.c_[ain[run] + side * (0.5 * k - 0.1), ys]
            out['pathEdges'].append(emit('pathEdges', poly_path(np.vstack([a2, b2[::-1]]), 3.0, adaptive=False),
                                         lambda X, Y: hex2rgb('D3B190') + 0.0 * X[..., None], cell=8.0))
            out['pathEdges'] += cobbles(pe, side, ys, rng)
    out['path'] += path_pebbles(pe, rng)
    return out


def cobbles(pe, side, ys, rng):
    """Lighter tan stones along the band, elongated along it, spaced 18-34 u."""
    out = []
    ain = 'rband_in' if side > 0 else 'lband_in'; aout = 'rband_out' if side > 0 else 'lband_out'
    y = ys[0] + rng.uniform(4, 20)
    while y < ys[-1] - 4:
        if y > 8:                                      # the seam's own cobbles are continued by the band field
            xi, xo = pe.at(ain, y), pe.at(aout, y)
            w = abs(xo - xi)
            if w > 22:
                u = rng.uniform(0.18, 0.82)
                cx = xi + (xo - xi) * u
                dx = (pe.at(ain, y + 2) - pe.at(ain, y - 2)) / 4
                ang = np.arctan2(1, dx)
                ry = rng.choice([rng.uniform(2.5, 4.5), rng.uniform(4.5, 8.5)], p=[0.6, 0.4]); rx = ry * rng.uniform(1.25, 1.8)
                out += pebble(cx, y, rx, ry, ang, seed=int(rng.integers(1 << 30)), layer='pathEdges', palette=COBBLE)
        y += rng.uniform(12, 40)
    return out


def path_pebbles(pe, rng, spacing=78.0):
    """Flat pebbles on the surface: Poisson-disc spaced, clear of the edges, flattened ovals."""
    pts = []
    tries = 0
    while tries < 4000:
        tries += 1
        y = rng.uniform(12, H - 4)
        L, R = pe.at('left', y), pe.at('right', y)
        x = rng.uniform(L + 22, R - 22)
        if all((x - a) ** 2 + (y - b) ** 2 > spacing ** 2 for a, b in pts):
            pts.append((x, y))
    out = []
    for x, y in pts:
        rx = rng.choice([rng.uniform(6, 11), rng.uniform(12, 22)], p=[0.55, 0.45])
        out += pebble(x, y, rx, rx * rng.uniform(0.55, 0.75), rng.uniform(-0.5, 0.5), seed=int(rng.integers(1 << 30)))
    return out


def build_ground(pe, objects=()):
    """Meadow base over the whole canvas (plus bleed) from a paint buffer: open-ground tone, soft shadows, halos."""
    buf = Buffer(-12, -12, W + 12, H + 12, res=0.5)
    noise = Noise(SEED + 2)
    buf.a[:] = 0.70 + 0.05 * noise(buf.X, buf.Y, 60.0) + 0.03 * noise(buf.X, buf.Y, 16.0)
    # pale bank strip along the band's outer edge (as the live art)
    for side, aout, bw in ((+1, pe.rband_out, pe.rbw), (-1, pe.lband_out, pe.lbw)):
        xe = np.interp(buf.Y, pe.y, aout); w = np.interp(buf.Y, pe.y, bw)
        d = side * (buf.X - xe)
        buf.a += 0.16 * np.exp(-np.clip(d, 0, None) / 7.0) * (d > -2) * np.clip(w / 25, 0, 1)
    for edge, bwn, side in (('left', 'lbw', -1), ('right', 'rbw', +1)):
        xe = np.interp(buf.Y, pe.y, getattr(pe, edge)); bw = np.interp(buf.Y, pe.y, getattr(pe, bwn))
        d = side * (buf.X - xe)
        buf.a += 0.13 * np.exp(-np.clip(d, 0, None) / 5.0) * (d > -3) * (1 - np.clip(bw / 25, 0, 1))
    for o in objects:
        o(buf)
    prof = seam_profile()
    gclean = S.clean_profile(prof, [(0, 37), (154, 176), (178, 234), (240, 366), (737, 884)])
    field = lambda X, Y: MEADOW(buf.sample(X, Y))
    poly = np.array([[-BLEED, -8], [W + BLEED, -8], [W + BLEED, H + BLEED], [-BLEED, H + BLEED]])
    from fx.geom import fmt, catmull_rom
    pathstr = 'M%g %gL%g %gL%g %gL%g %gZ' % (-BLEED, -8, W + BLEED, -8, W + BLEED, H + BLEED, -BLEED, H + BLEED)
    gfield = seam_blend(field, 90, gclean)
    return [emit('meadow', pathstr, gfield)], gfield


def build_caps(pe):
    """Continue the live features cut by the bottom edge."""
    live = load_live_layers()
    prof = seam_profile()
    xs = np.arange(len(prof)) + 0.5
    pf = lambda X: np.stack([np.interp(X, xs, prof[:, c]) for c in range(3)], -1)
    out = []
    # cut pebble on the path (live path shapes #6 + rims #69, #90): one cap spanning the rim-to-rim interval
    peb = [s for s in live if s.layer == 'path' and s.box[3] - 1 > H and 530 < s.box[0] + 1 < 620 and s.box[2] - s.box[0] < 90]
    if peb:
        xl = min(c[0] for s in peb for c in S.crossings(s)); xr = max(c[0] for s in peb for c in S.crossings(s))
        tl = S.tangent_at(max(peb, key=lambda s: s.box[2] - s.box[0]), xl); tr = S.tangent_at(max(peb, key=lambda s: s.box[2] - s.box[0]), xr)
        o = S.cap_outline(xl, tl, xr, tr, depth=5.0)
        def f(X, Y):
            base = pf(X)
            rim = hex2rgb('E3C295')
            k = np.clip(Y / 5.0, 0, 1)[..., None]
            return base * (1 - k) + rim * k
        out.append(('path', S.cap_shape('path', o, f)))
    return out


def generic_caps():
    """Continue every live object shape cut by the bottom edge: each crossing interval [xl, xr] closes with a
    tangent-matched rounded cap below the seam (depth ~0.45 x width, 4..36 u); colour = the live shape's colour at the
    seam row, carried down and darkened ~10 % toward the cap bottom (undersides are darker). Ground-coloured and
    path shapes are continued by the ground/path fields instead."""
    from fx.specimen import live, groundlike
    out = []
    for i, s in enumerate(live()):
        if s.layer in ('path', 'pathEdges') or s.box[3] - 1 <= H or s.box[1] + 1 >= H - 0.5:
            continue
        cr = S.crossings(s)
        for (xl, dl), (xr, dr) in zip(cr[0::2], cr[1::2]):
            w = xr - xl
            if w < 1.5:
                continue
            xm = np.array([(xl + xr) / 2]); c = s.colour_at(xm, np.array([H + 2.0]))[0]
            if groundlike(c[None])[0]:
                continue
            tl, tr = S.tangent_at(s, xl), S.tangent_at(s, xr)
            tl = tl + np.array([0, 1.0]); tl /= np.hypot(*tl)       # lean toward vertical: lobe bottoms, not drips
            tr = tr + np.array([0, 1.0]); tr /= np.hypot(*tr)
            depth = float(np.clip(0.22 * w, 2.5, 12))
            o = S.cap_outline(xl, tl, xr, tr, depth=depth)
            o[:, 1] -= 0.0
            def f(X, Y, s=s, depth=depth):
                C = s.colour_at(np.asarray(X), np.full(np.shape(X), H + 2.0))
                kk = (0.10 * np.clip(Y / depth, 0, 1) ** 1.5)[..., None]
                return C * (1 - kk)
            sh = S.cap_shape(s.layer, o, f, cell=2.0)
            sh.region = i
            out.append(sh)
    return out


def build():
    """Full extension. Elements are placed back to front by base y within each layer."""
    from fx import composites as C
    from fx.oldtree import old_tree
    from fx.water import Stream, stream
    from fx.plants import flower
    import specimens
    rng = np.random.default_rng(SEED)
    pm = path_model()
    pe = PathEdges(pm)
    layers = {L: [] for L in ('meadow', 'hedge', 'pathEdges', 'path', 'pond', 'backTrees', 'pines', 'bridge', 'bushes',
                              'doorBush', 'door', 'stones', 'rocks', 'fox', 'log', 'flowers', 'frontTrees')}
    gshapes, G = build_ground(pe)
    layers['meadow'] += gshapes
    for L, shapes in build_path(pe, rng).items():
        layers[L] += shapes
    for L, sh in build_caps(pe):
        layers[L].append(sh)

    def edge_x(name, side, scale, mirror):
        """dst x so that the specimen's canvas-edge cut lands on the extension's `side` edge."""
        sp = C.spec(name)
        cut = min(s.box[0] for _, s, k in sp.pieces if k == 'object') + 1   # source left-most x (cut at x ~ 0)
        if cut > 3:
            cut = max(s.box[2] for _, s, k in sp.pieces if k == 'object') - 1
        edge = -7.0 if side == 'left' else W + 7.0          # cut lands in the bleed, outside the canvas
        sgn = -1 if mirror else 1
        return edge - sgn * (cut - sp.ox) * scale

    groups = []                                           # (base_y, shapes)
    def add(y, shapes):
        groups.append((y, shapes))

    # ---- band A: join (0-560) ------------------------------------------------------------------------------
    add(450, C.generic('trees_ml', edge_x('trees_ml', 'right', 1.4, True), 450, G, size=1.4, seed=11, mirror=True, rot=0.0, exact=True, keep=NOFLOWER, sy=1.0))
    add(215, C.bush(640, 215, G, size=0.85, seed=12, source='bush_bridge'))
    add(300, C.rock(752, 300, G, size=0.62, seed=13, kind='rock_big'))
    add(300, C.fern(522, 300, G, size=0.9, seed=14, source='fern_rockleft'))
    add(472, C.pine(628, 472, G, size=0.68, seed=22, source='pine_top'))
    add(486, C.bush(530, 486, G, size=0.72, seed=23, source='bush_rightbridge'))
    add(505, C.fern(712, 505, G, size=0.85, seed=24, source='fern_rockleft'))
    add(40, C.fern(330, 40, G, size=0.8, seed=25, source='tuft_b'))
    add(330, C.pine(95, 330, G, size=0.72, seed=15, source='pine_top'))
    add(205, C.rock(150, 205, G, size=1.45, seed=16, kind='rock_seam'))
    add(560, C.bush(48, 560, G, size=0.72, seed=17, source='bush_rightbridge'))
    add(95, C.fern(70, 95, G, size=0.9, seed=18, source='tuft_b'))
    add(130, C.fern(560, 130, G, size=0.8, seed=19, source='tuft_a'))
    add(450, C.fern(540, 452, G, size=0.9, seed=20, source='tuft_a'))
    # ---- band B: denser (560-1120) -------------------------------------------------------------------------
    add(1110, C.generic('trees_bl', edge_x('trees_bl', 'left', 0.85, False), 1110, G, size=0.85, seed=21, mirror=False, rot=0.0, exact=True, keep=NOFLOWER, merge='backTrees'))
    for j, (x, y, src, sz) in enumerate([(70, 1138, 'bush_bridge', 0.78), (165, 1125, 'fern_rockleft', 1.0), (12, 1130, 'fern_rockleft', 0.9),
                                         (190, 735, 'fern_rockleft', 0.95), (205, 905, 'bush_rightbridge', 0.7), (515, 640, 'fern_rockleft', 0.85),
                                         (560, 772, 'tuft_a', 1.0), (612, 905, 'fern_rockleft', 0.9)]):
        add(y, C.fern(x, y, G, size=sz, seed=30 + j, source=src) if src != 'bush_bridge' else C.bush(x, y, G, size=sz, seed=30 + j, source=src))
    add(962, old_tree(845, 962, G, 0.85, seed=5))
    add(1010, C.pine(228, 1010, G, size=0.62, seed=46, source='pine_low'))
    add(690, C.bush(62, 690, G, size=0.7, seed=47, source='bush_bridge'))
    add(800, C.rock(262, 800, G, size=0.42, seed=48, kind='rock_big'))
    add(792, C.bush(566, 792, G, size=0.72, seed=42, source='bush_bridge'))
    add(1082, C.bush(292, 1082, G, size=0.66, seed=43, source='bush_rightbridge'))
    add(985, C.fern(690, 985, G, size=0.8, seed=45, source='tuft_a'))
    add(1078, C.rock(872, 1078, G, size=1.15, seed=41, kind='rock_seam'))
    # ---- band C: glade with stream (1120-1678) -------------------------------------------------------------
    st = Stream([(-30, 1180), (80, 1222), (178, 1310), (226, 1405), (205, 1500), (212, 1590), (205, 1700)],
                [(0, 22), (0.3, 27), (0.42, 58), (0.56, 56), (0.7, 28), (1, 30)])
    layers['pond'] += stream(st, (-40, 1150, 330, H + 10), seed=51)
    add(1446, C.generic('pad', 196, 1418, G, size=0.9, seed=55, rot=0.3))
    add(1460, C.generic('lily', 230, 1478, G, size=0.75, seed=56, rot=0.2))
    add(1500, C.generic('reeds', 168, 1508, G, size=0.75, seed=57, rot=0.0, mirror=False))
    add(1300, C.bush(300, 1290, G, size=0.6, seed=58, source='bush_bridge'))
    add(1565, C.fern(630, 1565, G, size=0.85, seed=59, source='fern_rockleft'))
    add(1683, C.generic('trees_br', edge_x('trees_br', 'left', 0.5, True), 1683, G, size=0.5, seed=52, mirror=True, rot=0.0, exact=True, keep=NOFLOWER))
    add(1683, C.generic('trees_bl', edge_x('trees_bl', 'right', 0.85, True), 1683, G, size=0.85, seed=53, mirror=True, rot=0.0, exact=True, keep=NOFLOWER))
    add(1660, C.bush(690, 1660, G, size=0.8, seed=54, source='bush_bridge'))
    for j, (x, y, sz) in enumerate([(340, 1235, 1.0), (98, 1300, 0.85), (300, 1468, 0.9), (110, 1560, 0.8), (650, 1475, 0.9),
                                    (380, 1380, 0.8), (330, 1640, 0.8), (420, 140, 0.7), (40, 820, 0.8), (600, 1030, 0.8)]):
        add(y, C.fern(x, y, G, size=sz, seed=60 + j, source=('tuft_a', 'tuft_b')[j % 2]))
    for j, (x, y, sc) in enumerate([(255, 1352, 0.8), (150, 1428, 0.7), (265, 1545, 0.75)]):
        add(y, C.generic('stone_pond', x, y, G, size=sc, seed=70 + j, rot=0.1))
    fl = [(330, 1190, 'white'), (352, 1215, 'yellow'), (318, 1330, 'lilac'), (360, 1420, 'white'), (300, 1515, 'yellow'),
          (690, 1555, 'white'), (705, 1590, 'lilac'), (95, 1410, 'white'), (60, 1620, 'yellow'), (640, 230, 'yellow'),
          (372, 1300, 'white'), (395, 1318, 'white'), (345, 1600, 'lilac'), (370, 1590, 'white'), (88, 1335, 'yellow'),
          (560, 640, 'white'), (580, 655, 'lilac'), (240, 1050, 'white'), (660, 1020, 'yellow'), (475, 540, 'lilac')]
    for j, (x, y, k) in enumerate(fl):
        add(y, flower(x, y, rng.uniform(10, 14), k, seed=80 + j))

    for y, shapes in sorted(groups, key=lambda t: t[0]):
        for sh in shapes:
            layers[sh.layer].append(sh)
    caps = generic_caps()
    for sh in caps:
        layers[sh.layer].append(sh)
    return layers, pm, pe
