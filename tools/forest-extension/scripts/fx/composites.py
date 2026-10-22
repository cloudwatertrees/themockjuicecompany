"""New elements recombined from live specimens (seeded): bushes, rocks, trees, pines, ferns.

Every builder returns PShapes in draw order. `ground(X, Y)` is the new ground colour field (for re-grounding the
specimens' ground pieces and for shadows)."""
import numpy as np
import specimens
from .specimen import place, recolour_fn
from .plants import flower
from .trees import light_side

_SPEC = {}


def spec(name):
    if name not in _SPEC:
        _SPEC[name] = specimens.get(name)
    return _SPEC[name]


def is_green(s):
    c = s.cols.mean(0)
    return c[1] > c[0] + 0.02 and c[1] > c[2] + 0.02


def is_flower_piece(s):
    c = s.cols.mean(0)
    small = max(s.box[2] - s.box[0], s.box[3] - s.box[1]) < 48
    pale = c.min() > 0.80                                   # petal backing painted into meadow/bushes
    return small and (s.layer == 'flowers' or (not is_green(s) and s.layer != 'meadow') or pale)


def flower_clusters(sp):
    """Source flowers: (centre x, centre y, radius, kind), anchored on each yellow centre piece; radius and kind from
    the smallest petal piece around it."""
    pcs = [s for _, s, k in sp.pieces if is_flower_piece(s)]
    out = []
    for s in pcs:
        c = s.cols.mean(0)
        if not (c[0] > 0.88 and c[1] > 0.66 and c[2] < 0.5):
            continue
        cx, cy = (s.box[0] + s.box[2]) / 2, (s.box[1] + s.box[3]) / 2
        best = None
        for t in pcs:
            if t is s:
                continue
            b = t.box
            w = max(b[2] - b[0], b[3] - b[1])
            tc = t.cols.mean(0)
            if b[0] < cx < b[2] and b[1] < cy < b[3] and 12 < w < 52 and not (tc[0] > 0.88 and tc[2] < 0.5):
                if best is None or w > best[0]:
                    best = (w, tc)
        if best is None:
            continue
        R = best[0] / 2 * 0.98
        tc = best[1]
        out.append((cx, cy, R, 'lilac' if tc[2] > tc[1] + 0.06 else 'white'))
    return out


def leaf_spots(shapes, n, rng, light):
    """Points on the lit upper half of a placed bush, spread out (for flowers)."""
    xs = np.array([[(s.box[0] + s.box[2]) / 2, (s.box[1] + s.box[3]) / 2] for s in shapes if s.layer == 'bushes'])
    if not len(xs):
        return []
    x0, y0 = xs.min(0); x1, y1 = xs.max(0)
    pts = []
    for _ in range(400):
        p = np.array([rng.uniform(x0 + 0.1 * (x1 - x0), x1 - 0.1 * (x1 - x0)), rng.uniform(y0 + 0.15 * (y1 - y0), y1 - 0.05 * (y1 - y0))])
        if all(np.hypot(*(p - q)) > 0.28 * (x1 - x0) for q in pts):
            pts.append(p)
        if len(pts) == n:
            break
    return pts


BUSH_SOURCES = ('bush_bridge', 'bush_rightbridge')


def flowered(name, x, base_y, ground, size=1.0, seed=0, kinds=('white', 'lilac'), mirror=None, rot=0.06, hue=0.012,
             keep_flowers=0.6, merge=None):
    """Specimen with its own flowers swapped: flower pieces removed, petal backings painted shade green, generated
    flowers placed at the transformed source flower centres (kind kept with p=keep_flowers)."""
    from .plants import LEAF
    rng = np.random.default_rng(seed)
    src = spec(name)
    if mirror is None:
        mirror = (light_side(src.ox) != light_side(x)) ^ bool(rng.random() < 0.25)
    rc = recolour_fn(hue=rng.uniform(-hue, hue), sat=rng.uniform(0.94, 1.06), val=rng.uniform(0.97, 1.03))
    shade = lambda s: (lambda u, v: LEAF(0.30 + 0.06 * np.clip((v - s.box[1]) / max(s.box[3] - s.box[1], 1), 0, 1))
                       * np.ones(np.shape(u) + (3,))) if (is_flower_piece(s) and s.layer != 'flowers') else None
    sc = size * rng.uniform(0.94, 1.06)
    out = place(src, (x, base_y), ground, scale=sc, mirror=mirror, rot=rng.uniform(-rot, rot), recolour=rc, seed=seed,
                keep=lambda o, s, k: s.layer != 'flowers' and not (is_flower_piece(s) and s.layer == 'meadow'),
                paint=shade, merge=merge or getattr(src, 'merge', None))
    T = place.last
    for i, (fx_, fy_, R, kind) in enumerate(flower_clusters(src)):
        p = T.fwd(np.array([[fx_, fy_]]))[0]
        k = kind if rng.random() < keep_flowers else kinds[int(rng.integers(len(kinds)))]
        out += flower(p[0], p[1], R * sc * rng.uniform(0.92, 1.06), k, seed=seed * 31 + i)
    return out


def bush(x, base_y, ground, size=1.0, seed=0, kinds=('white', 'lilac'), source=None):
    return flowered(source or BUSH_SOURCES[seed % len(BUSH_SOURCES)], x, base_y, ground, size, seed, kinds, merge='bushes')


def pine(x, base_y, ground, size=1.0, seed=0, kinds=('white', 'yellow', 'lilac'), source=None):
    return flowered(source or ('pine_top', 'pine_low')[seed % 2], x, base_y, ground, size, seed, kinds, rot=0.03, merge='pines')


def fern(x, base_y, ground, size=1.0, seed=0, source=None):
    rng = np.random.default_rng(seed)
    src = source or ('fern_rockleft', 'tuft_a', 'tuft_b', 'bush_rightbridge')[int(rng.integers(4))]
    if src == 'bush_rightbridge':
        return flowered(src, x, base_y, ground, size, seed, merge='bushes')
    return generic(src, x, base_y, ground, size=size, seed=seed, rot=0.15, mirror=bool(rng.random() < 0.5))


def generic(name, x, base_y, ground, size=1.0, seed=0, keep=None, mirror=None, rot=0.08, hue=0.01, sy=1.0, wob=0.6, merge=None, exact=False):
    """Any specimen, mirrored to the new light side (or flipped at random when the light allows), rescaled (sy =
    extra vertical factor), slightly rotated and recoloured."""
    rng = np.random.default_rng(seed)
    src = spec(name)
    if mirror is None:
        mirror = light_side(src.ox) != light_side(x)
    rc = recolour_fn(hue=rng.uniform(-hue, hue), sat=rng.uniform(0.95, 1.05), val=rng.uniform(0.97, 1.03))
    sc = size * (1.0 if exact else rng.uniform(0.95, 1.05))
    return place(src, (x, base_y), ground, scale=sc, mirror=mirror, rot=rng.uniform(-rot, rot), sy=sc * sy,
                 recolour=rc, seed=seed, keep=keep, wob=wob, merge=merge or getattr(src, 'merge', None))


def rock(x, base_y, ground, size=1.0, seed=0, kind=None):
    """Boulder from a live rock specimen (big faceted boulder, or the small seam rock group)."""
    rng = np.random.default_rng(seed)
    kind = kind or ('rock_big' if rng.random() < 0.6 else 'rock_seam')
    return generic(kind, x, base_y, ground, size=size, seed=seed, rot=0.05, sy=rng.uniform(0.92, 1.08))
