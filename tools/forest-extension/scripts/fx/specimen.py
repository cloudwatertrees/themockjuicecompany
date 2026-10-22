"""Live-art specimens: pick the real pieces of a live element, then place transformed copies (mirror, scale, rotate,
recolour, perturb) anywhere in the extension, seeded and deterministic.

Pieces are classified as `object` (foliage, rock, flower...) or `ground` (meadow-coloured shadows, halos and ground
patches that the traced mosaic carries around each object). Object pieces keep their own painted colours (optionally
recoloured). Ground pieces are re-grounded: new colour = new ground x (live colour / live ground at the source point),
so a shadow stays a shadow and a halo stays a halo, and pieces whose colour equalled the live ground melt into the new
ground without an edge."""
import os
import numpy as np
from scipy import ndimage as ndi
from common import load_live_layers, render, SCRATCH, W, H, LAYERS
from art import flatten
from pbart import PShape
from .geom import multi_path, poly_path
from .paint import emit, area
from .irregular import wobble

_LIVE = None
_GROUND = None


def live():
    global _LIVE
    if _LIVE is None:
        _LIVE = load_live_layers()
    return _LIVE


def groundlike(rgb):
    R, G, B = rgb[..., 0] * 255, rgb[..., 1] * 255, rgb[..., 2] * 255
    return (R > 120) & (G > 120) & (B < 205) & (np.abs(R - G) < 36) & (B < G - 18)


def live_ground():
    """Smooth estimate of the bare ground colour under the whole live canvas (1 sample/u): normalised convolution of
    ground-like pixels, so foliage, rocks, path and water are filled from the ground around them."""
    global _GROUND
    if _GROUND is not None:
        return _GROUND
    p = SCRATCH / 'live_ground.npy'
    if p.exists():
        _GROUND = np.load(p); return _GROUND
    img = render(live(), 1.0, (0, 0, W, H), S=4)
    m = groundlike(img).astype(float)
    out = np.zeros_like(img); done = np.zeros(m.shape, bool)
    for sig in (6, 12, 24, 48, 96, 200):
        den = ndi.gaussian_filter(m, sig)
        num = np.stack([ndi.gaussian_filter(img[..., c] * m, sig) for c in range(3)], -1)
        f = num / np.maximum(den, 1e-6)[..., None]
        take = ~done & (den > (0.2 if sig < 200 else 1e-6))
        out[take] = f[take]; done |= take
    _GROUND = out
    np.save(p, out)
    return out


def sample_img(img, X, Y, x0=0.0, y0=0.0, res=1.0):
    u = (np.asarray(X) - x0) * res - 0.5; v = (np.asarray(Y) - y0) * res - 0.5
    return np.stack([ndi.map_coordinates(img[..., c], [v.ravel(), u.ravel()], order=1, mode='nearest')
                     for c in range(3)], -1).reshape(np.shape(X) + (3,))


def live_ground_at(X, Y):
    return sample_img(live_ground(), X, Y)


class Specimen:
    def __init__(self, name, box, layers=None, pick=None, margin=6, exclude=None, max_size=None, ground_max=None):
        """Live pieces whose centre lies inside `box` and whose bounds stay within `margin` of it, in `layers`
        (default all), passing `pick`. Ground pieces larger than `ground_max` (u) are skipped."""
        self.name, self.box = name, box
        x0, y0, x1, y1 = box
        self.pieces = []                                  # (order, shape, kind)
        for i, s in enumerate(live()):
            b = s.box
            if layers and s.layer not in layers:
                continue
            mx, my = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            if not (x0 <= mx <= x1 and y0 <= my <= y1):
                continue
            if not (b[0] >= x0 - margin and b[2] <= x1 + margin and b[1] >= y0 - margin and b[3] <= y1 + margin):
                continue
            if max_size and max(b[2] - b[0], b[3] - b[1]) > max_size:
                continue
            if pick and not pick(s):
                continue
            if exclude and exclude(s):
                continue
            kind = self.classify(s)
            if kind == 'ground' and ground_max and max(b[2] - b[0], b[3] - b[1]) > ground_max:
                continue
            self.pieces.append((i, s, kind))
        self.cx = (x0 + x1) / 2
        xs = [s.box[0] for _, s, k in self.pieces if k == 'object'] + [s.box[2] for _, s, k in self.pieces if k == 'object']
        self.ox = (min(xs) + max(xs)) / 2 if xs else self.cx
        ys = [s.box[3] for _, s, k in self.pieces if k == 'object']
        self.base_y = max(ys) if ys else y1               # lowest object point = where it stands

    @staticmethod
    def classify(s):
        """'ground' for meadow-layer pieces and for pieces whose colour is (nearly) the live ground under them;
        everything else (leaves of any green, petals, rock, halos painted as part of the object) is 'object'."""
        c = s.cols.mean(0)
        if s.layer == 'meadow' and groundlike(c[None])[0]:
            return 'ground'
        x0, y0, x1, y1 = s.box
        g = live_ground_at(np.array([(x0 + x1) / 2]), np.array([(y0 + y1) / 2]))[0]
        return 'ground' if np.abs(c - g).max() < 0.05 else 'object'

    def counts(self):
        return {'object': sum(k == 'object' for *_, k in self.pieces), 'ground': sum(k == 'ground' for *_, k in self.pieces)}


def recolour_fn(hue=0.0, sat=1.0, val=1.0, warm=0.0):
    """RGB -> RGB: rotate hue (turns), scale saturation / value, add a warm (+) / cool (-) shift."""
    if hue == 0 and sat == 1 and val == 1 and warm == 0:
        return lambda C: C
    def f(C):
        C = np.asarray(C, float)
        mx = C.max(-1); mn = C.min(-1); d = mx - mn
        h = np.zeros_like(mx)
        r, g, b = C[..., 0], C[..., 1], C[..., 2]
        m = d > 1e-6
        rc = np.where(m, (mx - r) / np.where(m, d, 1), 0); gc = np.where(m, (mx - g) / np.where(m, d, 1), 0)
        bc = np.where(m, (mx - b) / np.where(m, d, 1), 0)
        h = np.where(r == mx, bc - gc, np.where(g == mx, 2 + rc - bc, 4 + gc - rc))
        h = (h / 6.0) % 1.0
        sv = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0)
        h = (h + hue) % 1.0; sv = np.clip(sv * sat, 0, 1); v = np.clip(mx * val, 0, 1)
        i = np.floor(h * 6).astype(int) % 6; fr = h * 6 - np.floor(h * 6)
        p = v * (1 - sv); q = v * (1 - sv * fr); t = v * (1 - sv * (1 - fr))
        out = np.stack([np.choose(i, [v, q, p, p, t, v]), np.choose(i, [t, v, v, q, p, p]), np.choose(i, [p, p, t, v, v, q])], -1)
        return np.clip(out + warm * np.array([1.0, 0.45, -0.6]), 0, 1)
    return f


class Placement:
    """Affine map source -> target: p' = A (p - src) + dst, A = rotation(rot) . diag(sx*mirror, sy)."""
    def __init__(self, src, dst, scale=1.0, mirror=False, rot=0.0, sy=None):
        sx = scale * (-1 if mirror else 1); sy = scale if sy is None else sy
        c, s = np.cos(rot), np.sin(rot)
        self.A = np.array([[c, -s], [s, c]]) @ np.diag([sx, sy])
        self.Ai = np.linalg.inv(self.A)
        self.src, self.dst = np.asarray(src, float), np.asarray(dst, float)

    def fwd(self, P):
        return (np.asarray(P) - self.src) @ self.A.T + self.dst

    def inv(self, X, Y):
        P = np.stack([np.asarray(X) - self.dst[0], np.asarray(Y) - self.dst[1]], -1) @ self.Ai.T + self.src
        return P[..., 0], P[..., 1]


def place(spec, dst, ground, scale=1.0, mirror=None, rot=0.0, sy=None, recolour=None, wob=0.6, seed=0,
          layer_map=None, keep=None, light_side_new=None, anchor=None, ground_gain=1.0, paint=None, merge=None):
    """Transformed copy of a specimen standing at `dst` (x, base y). `ground(X, Y)` = the new ground colour field.
    mirror=None: mirror automatically when the light side differs between source and target position.
    keep(order, shape, kind) -> bool selects pieces. Returns PShapes in source draw order."""
    from .trees import light_side
    if mirror is None:
        mirror = light_side(spec.ox) != light_side(dst[0])
    src = anchor if anchor is not None else (spec.ox, spec.base_y)
    T = Placement(src, dst, scale, mirror, rot, sy)
    place.last, place.last_scale = T, scale
    rc = recolour or (lambda C: C)
    out = []
    for k, (order, s, kind) in enumerate(spec.pieces):
        if keep and not keep(order, s, kind):
            continue
        polys = [T.fwd(P) for P in flatten(s.subs, 4.0 / max(scale, 0.3))]
        if wob > 0 and area(s.subs) * scale * scale > 30:
            polys = wobble(polys, s.layer, wob, seed + k)
        layer = (layer_map or {}).get(s.layer, s.layer)
        if merge:                                         # one target layer for the objects, source order kept
            layer = 'meadow' if kind == 'ground' else merge
        if paint is not None and paint(s) is not None:
            def field(X, Y, s=s, pf=paint(s)):
                u, v = T.inv(X, Y)
                return pf(u, v)
        elif kind == 'object':
            def field(X, Y, s=s):
                u, v = T.inv(X, Y)
                return rc(s.colour_at(u, v))
        else:
            def field(X, Y, s=s):
                u, v = T.inv(X, Y)
                ratio = s.colour_at(u, v) / np.maximum(live_ground_at(u, v), 0.05)
                ratio = 1 + (ratio - 1) * ground_gain
                return np.clip(ground(X, Y) * ratio, 0, 1)
        cell = 8.0 if (s.nx > 2 and (s.box[2] - s.box[0]) / max(s.nx - 1, 1) > 6) else 4.0
        pathstr = multi_path(polys, step=2.0)
        if not pathstr:
            continue
        sh = emit(layer, pathstr, field, cell=cell)
        sh.region = order
        out.append(sh)
    if merge:                                             # ground pieces first (they lie under everything)
        out = [o for o in out if o.layer == 'meadow'] + [o for o in out if o.layer != 'meadow']
    return out
