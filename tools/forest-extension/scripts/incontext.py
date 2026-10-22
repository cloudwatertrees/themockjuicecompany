"""In-context harness: replace one live element by a recipe's output in place and view it beside the original.

The live element's shapes are removed; the hole is filled by a ground underlay (mesh sampled from the surrounding live
pixels, normalised-convolution fill) in the element's own layer; the recipe's shapes (and its ground shadow, if any)
are inserted in their true layers; every other live shape stays, in order. Both panels: same crop, same scale.

usage: python incontext.py NAME [seed] [scale]      (NAME from ELEMENTS below)
"""
import sys
import numpy as np
from scipy import ndimage as ndi
from common import *
from art import rasterize, rgb2hex
from fx.geom import Grid, multi_path
from fx.paint import emit


def element_mask(shapes, box, sc):
    x0, y0, x1, y1 = box
    Wp, Hp = int(round((x1 - x0) * sc)), int(round((y1 - y0) * sc))
    m = np.zeros((Hp, Wp))
    for s in shapes:
        r = rasterize(flatten(s.subs, sc), sc, -x0 * sc, -y0 * sc, Wp, Hp, 4)
        if r:
            a, b, c = r; h, w = c.shape
            m[b:b + h, a:a + w] = np.maximum(m[b:b + h, a:a + w], c)
    return m


class Context:
    def __init__(self, box, pick, pad=40):
        """box: crop (x0, y0, x1, y1); pick(shape) -> True for the live shapes forming the element."""
        self.box = box
        from fx.specimen import live
        self.live = live()                                # shared with the specimens, so picks by identity work
        self.removed = [s for s in in_box(self.live, box, pad) if pick(s)]
        ids = set(map(id, self.removed))
        self.kept = [s for s in self.live if id(s) not in ids]
        order = {id(s): i for i, s in enumerate(self.live)}
        self.first_removed = min((order[id(s)] for s in self.removed), default=0)
        self.order = order
        self.layer = self.removed[0].layer if self.removed else 'meadow'
        self.underlay = self._underlay(pad)

    def _underlay(self, pad, res=1.0):
        """Ground patch over the removed footprint: colours of the surrounding live render, filled inward."""
        if not self.removed:
            return []
        x0, y0, x1, y1 = self.box
        bx = (x0 - pad, y0 - pad, x1 + pad, y1 + pad)
        img = render(in_box(self.kept, bx, 4), res, bx)              # without the element
        orig = render(in_box(self.live, bx, 4), res, bx)
        m = element_mask(self.removed, bx, res)
        m = ndi.binary_dilation(m > 0.02, iterations=2)
        # only where no kept object shape covers the hole (else the live neighbours beneath already show)
        objs = [s for s in in_box(self.kept, bx, 4) if s.layer not in ('meadow', 'path', 'pathEdges', 'pond')]
        cover = element_mask(objs, bx, res) > 0.98
        m = m & ~cover
        # pixels that belong to the element's ground in the original but not to foliage: use the original render
        # around the element, excluding the element itself
        R, G, B = (orig[..., c] * 255 for c in range(3))
        groundlike = (R > 150) & (G > 150) & (B < 200) & (np.abs(R - G) < 35) & (B < G - 20)
        known = ~m & groundlike
        src = orig * known[..., None]
        out = np.zeros_like(src); wsum = np.zeros(m.shape)
        for sig in (3, 6, 12, 24, 48, 96, 192):
            num = np.stack([ndi.gaussian_filter(src[..., c], sig) for c in range(3)], -1)
            den = ndi.gaussian_filter(known.astype(float), sig)
            fill = num / np.maximum(den, 1e-6)[..., None]
            take = (wsum < 0.5) & (den > (0.15 if sig < 96 else 1e-4))
            out[take] = fill[take]; wsum[take] = 1
        out[~m] = orig[~m]
        self.fill_img, self.fill_box, self.fill_res = out, bx, res
        g = Grid(*bx, res=1.0)
        mm = ndi.zoom(m.astype(float), (g.ny / m.shape[0], g.nx / m.shape[1]), order=1)
        polys = g.contours(0.5 - ndi.binary_dilation(mm > 0.5, iterations=1).astype(float), level=0.0, min_area=4)
        if not polys:
            return []
        return [emit(self.layer, multi_path(polys, step=3.0), self.ground_field)]

    def ground_field(self, X, Y):
        x0, y0 = self.fill_box[0], self.fill_box[1]
        u = (np.asarray(X) - x0) * self.fill_res; v = (np.asarray(Y) - y0) * self.fill_res
        return np.stack([ndi.map_coordinates(self.fill_img[..., c], [v.ravel(), u.ravel()], order=1, mode='nearest')
                         for c in range(3)], -1).reshape(np.shape(X) + (3,))

    def compose(self, new):
        """new: list of PShapes (any layers). True order: per layer, kept live shapes, then underlay, then new."""
        out = []
        for L in LAYERS:
            if L == self.layer:                          # element layer: neighbours behind, underlay, new, neighbours in front
                before = [s for s in self.kept if s.layer == L and self.order[id(s)] < self.first_removed]
                after = [s for s in self.kept if s.layer == L and self.order[id(s)] > self.first_removed]
                out += before + self.underlay + [s for s in new if s.layer == L] + after
            else:
                out += [s for s in self.kept if s.layer == L] + [s for s in new if s.layer == L]
        return out

    def view(self, new, sc, path):
        box = self.box
        a = render(in_box(self.live, box, 4), sc, box)
        b = render(in_box(self.compose(new), box, 4), sc, box)
        sep = np.ones((a.shape[0], 4, 3))
        save(np.concatenate([a, sep, b], 1), path)
        return path


# ---- element registry ------------------------------------------------------------------------------------------
def near(c, hexes, tol=0.12):
    from art import hex2rgb
    m = c.cols.mean(0)
    return any(np.abs(m - hex2rgb(h)).max() < tol for h in hexes)


def is_flower(s):
    m = s.cols.mean(0)
    small = s.box[2] - s.box[0] < 45 and s.box[3] - s.box[1] < 45
    return small and (m.min() > 0.72 or near(s, ['FDD350', 'FBE263', 'D6A1EA', 'C995E0'], 0.12))


def E_pine(seed):
    from fx.plants import fern_pine
    box = (325, 405, 505, 650)
    pick = lambda s: s.layer == 'pines' and s.box[1] < 640 and not is_flower(s)
    return box, pick, lambda ctx: fern_pine(415, 432, 80, tiers=3, seed=seed, ground=ctx.ground_field)


def E_flowers(seed):
    from fx.plants import flower
    box = (240, 900, 440, 1060)
    pick = lambda s: (s.box[2] - s.box[0] < 45 and s.box[3] - s.box[1] < 45 and
                      (near(s, ['F6F5D8', 'F9F5D6', 'F8F5D5', 'FCF8E6']) or near(s, ['D6A1EA', 'C995E0', 'CC9BE2'], 0.14) or near(s, ['FDD350', 'FBE263'], 0.14)))
    def build(ctx):
        return (flower(323, 965, 23, 'white', seed) + flower(366, 982, 17.5, 'white', seed + 1) +
                flower(414, 982, 17, 'lilac', seed + 2) + flower(392, 1013, 18, 'lilac', seed + 3))
    return box, pick, build


def E_bush(seed):
    from fx.plants import leaf_clump, flower
    box = (225, 880, 435, 1050)
    pick = lambda s: s.layer in ('bushes', 'flowers') and 230 < (s.box[0] + s.box[2]) / 2 < 430 and 885 < (s.box[1] + s.box[3]) / 2 < 1050
    def build(ctx):
        sh = leaf_clump(318, 990, 78, seed=seed)
        sh += flower(322, 965, 17, 'white', seed) + flower(361, 982, 13, 'white', seed + 1)
        sh += flower(408, 980, 12, 'lilac', seed + 2) + flower(383, 1012, 13, 'lilac', seed + 3)
        return sh
    return box, pick, build


def E_rock(seed):
    from fx.stones import rock
    box = (520, 840, 770, 1025)
    pick = lambda s: s.layer == 'rocks' and 530 < (s.box[0] + s.box[2]) / 2 < 760 and 840 < (s.box[1] + s.box[3]) / 2 < 1020
    return box, pick, lambda ctx: rock(620, 997, 150, 140, seed) + rock(690, 1005, 40, 32, seed + 1) + rock(646, 1013, 46, 30, seed + 2)


def E_tree(seed):
    from fx.trees import bell_tree
    box = (40, 1150, 290, 1420)
    pick = lambda s: s.layer == 'frontTrees' and 100 < (s.box[0] + s.box[2]) / 2 < 240 and 1180 < (s.box[1] + s.box[3]) / 2 < 1400 and s.box[2] - s.box[0] < 180
    return box, pick, lambda ctx: bell_tree(152, 1218, 66, tiers=3, seed=seed)


def E_bushspec(seed):
    import specimens
    from fx.specimen import place
    box = (225, 880, 435, 1050)
    pick = lambda s: s.layer in ('bushes', 'flowers') and 230 < (s.box[0] + s.box[2]) / 2 < 430 and 885 < (s.box[1] + s.box[3]) / 2 < 1050
    def build(ctx):
        from fx.composites import bush
        return bush(331, 1035, ctx.ground_field, size=1.0, seed=seed)
    return box, pick, build


def E_rockspec(seed):
    import specimens
    box = (500, 830, 790, 1040)
    ids = {id(s) for _, s, k in specimens.get('rock_big').pieces if k == 'object'}
    pick = lambda s: id(s) in ids
    def build(ctx):
        from fx.composites import rock
        if seed % 2 == 0:
            return rock(640, 1019, ctx.ground_field, size=0.9, seed=seed, kind='rock_big')
        return rock(640, 1019, ctx.ground_field, size=1.9, seed=seed, kind='rock_seam')
    return box, pick, build


def E_treespec(seed):
    import specimens
    box = (-10, 1060, 320, 1620)
    ids = {id(s) for _, s, k in specimens.get('trees_bl').pieces if k == 'object'}
    pick = lambda s: id(s) in ids
    def build(ctx):
        from fx.composites import generic
        name, x, y, sc = [('trees_tl', 140, 1580, 1.25), ('trees_tr', 120, 1590, 1.2), ('tree_bell', 150, 1440, 1.0)][seed % 3]
        return generic(name, x, y, ctx.ground_field, size=sc, seed=seed, rot=0.03)
    return box, pick, build


def E_pinespec(seed):
    import specimens
    box = (300, 395, 530, 665)
    ids = {id(s) for _, s, k in specimens.get('pine_top').pieces if k == 'object'}
    pick = lambda s: id(s) in ids
    def build(ctx):
        from fx.composites import pine
        return pine(418, 658, ctx.ground_field, size=[1.0, 0.95, 1.05][seed % 3], seed=seed + 1, source=['pine_low', 'pine_top', 'pine_low'][seed % 3])
    return box, pick, build


ELEMENTS = {k[2:]: v for k, v in globals().items() if k.startswith('E_')}

if __name__ == '__main__':
    name = sys.argv[1]; seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    sc = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    box, pick, build = ELEMENTS[name](seed)
    ctx = Context(box, pick)
    new = build(ctx)
    out = ctx.view(new, sc, SCRATCH / f'ic_{name}.png')
    print(out, len(ctx.removed), 'removed', len(new), 'new')
