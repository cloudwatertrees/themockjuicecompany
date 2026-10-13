"""v2: per-pixel layer map for the new reference.
Unchanged areas take the current art's (pb32) topmost layer; hand-placed polygons mark the new objects; inside the
changed areas, remaining pixels are classified by colour (bush green vs meadow). Flowers come from colour masks.
usage: v2_layermap.py OUT.npy [PREVIEW.png]   (run from the working copy's tools/)"""
import sys, numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2lab, rgb2hsv
from art import LAYERS, W, H, flatten, rasterize
from pbart import load
from score import SP

L = {n: i for i, n in enumerate(LAYERS)}
POLY = {
    'pond': [[(0, 325), (60, 318), (150, 316), (235, 332), (300, 378), (345, 425), (345, 470), (295, 500), (200, 507),
              (120, 527), (75, 545), (0, 548)]],
    'bridge': [[(100, 700), (140, 640), (285, 588), (328, 588), (447, 698), (462, 822), (422, 845), (312, 907),
                (228, 907), (188, 860), (148, 800), (100, 772)]],
    'rocks': [[(725, 700), (770, 640), (830, 630), (880, 680), (905, 760), (912, 862), (820, 872), (728, 862)],
              [(540, 960), (570, 903), (640, 893), (700, 918), (732, 958), (762, 975), (748, 1022), (640, 1012), (543, 1002)],
              [(108, 1600), (150, 1583), (200, 1588), (247, 1640), (247, 1678), (108, 1678)]],
    'log': [[(688, 1000), (760, 984), (892, 988), (907, 1050), (822, 1097), (700, 1127), (683, 1080)]],
}
OLD_GONE = ['door', 'fox', 'stones', 'bridge', 'flowers']      # their old footprints changed

def poly_mask(polys):
    m = np.zeros((H, W), np.uint8)
    for p in polys:
        cv2.fillPoly(m, [np.array(p, np.int32)], 1)
    return m.astype(bool)

def old_layers():
    lab = np.full((H, W), L['meadow'], np.int16); best = np.zeros((H, W), np.float32)
    for sh in load(SP + 'data/pb32'):
        r = rasterize(flatten(sh.subs, 1.0), 1.0, 0, 0, W, H, 4)
        if r is None: continue
        x0, y0, c = r; sub = lab[y0:y0 + c.shape[0], x0:x0 + c.shape[1]]
        sub[c >= 0.5] = L[sh.layer]                                # later shapes are on top
    return lab

def flower_mask(ref):
    hsv = rgb2hsv(ref); h, s, v = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
    lab = rgb2lab(ref)
    purple = (h > 260) & (h < 325) & (s > 0.25) & (v > 0.45)
    yellow = (h > 40) & (h < 62) & (s > 0.45) & (v > 0.8)
    white = (lab[..., 0] > 90) & (np.hypot(lab[..., 1], lab[..., 2]) < 9)
    m = ndi.binary_closing(purple | yellow | white, iterations=1)
    lbl, n = ndi.label(m)
    keep = np.zeros(n + 1, bool)
    for i, sl in enumerate(ndi.find_objects(lbl), 1):
        comp = lbl[sl] == i; a = comp.sum()
        if a < 40 or a > 4000: continue
        frac_y = (yellow[sl] & comp).sum() / a; frac_p = (purple[sl] & comp).sum() / a
        # daisies: white petals with a yellow centre; purple and yellow flowers by their own colour
        if frac_p > 0.5 or (frac_y > 0.08 and (white[sl] & comp).sum() / a > 0.3) or frac_y > 0.6:
            keep[i] = True
    return ndi.binary_dilation(keep[lbl], iterations=1)

if __name__ == '__main__':
    ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
    lab = old_layers()
    rl = rgb2lab(ref)
    changed = np.isin(lab, [L[n] for n in OLD_GONE])
    for n, polys in POLY.items():
        changed |= poly_mask(polys)
    changed = ndi.binary_dilation(changed, iterations=4)
    # inside changed areas: bush green vs meadow by lightness/chroma; doorBush on the right side
    green = (rl[..., 0] < 78) & (rl[..., 1] < -8)
    yy, xx = np.mgrid[0:H, 0:W]
    right = (xx > 640) & (yy > 540) & (yy < 965)
    m = changed & np.isin(lab, [L[n] for n in OLD_GONE + ['meadow', 'bushes', 'doorBush']])
    lab[m & green & right] = L['doorBush']
    lab[m & green & ~right] = L['bushes']
    lab[m & ~green] = L['meadow']
    # object polygons: claim only pixels that do not look like the background they sit on (pale meadow, path
    # cream, or the dirt border matching its colour just outside the polygon)
    from skimage.color import deltaE_ciede2000
    pale = (rl[..., 0] > 82) & (rl[..., 1] < 4) & (rl[..., 2] > 8)
    allpoly = np.zeros((H, W), bool)
    for polys in POLY.values():
        allpoly |= poly_mask(polys)
    ring = ndi.binary_dilation(allpoly, iterations=12) & ~allpoly
    dirt = np.median(rl[ring & (lab == L['pathEdges'])], 0)
    dirt_like = (lab == L['pathEdges']) & (deltaE_ciede2000(rl, dirt[None, None]) < 10)
    for n, polys in POLY.items():
        poly = poly_mask(polys)
        core = poly & ~pale & ~dirt_like
        if n == 'pond':
            core &= ~(green & (xx > 280) & (yy < 395))         # the bush at the pond's top right
        else:
            core &= ~green                                       # neighbouring bushes; enclosed moss returns below
        pm = ndi.binary_fill_holes(ndi.binary_closing(ndi.binary_opening(core, iterations=1), iterations=3)) & poly
        lab[pm] = L[n]
    fm = flower_mask(ref) & ~np.isin(lab, [L['path'], L['pathEdges']])
    lab[fm] = L['flowers']
    np.save(sys.argv[1], lab)
    print({n: int((lab == i).sum()) for n, i in L.items()})
    if len(sys.argv) > 2:
        rng = np.random.default_rng(3); pal = rng.integers(40, 255, (len(LAYERS), 3)); pal[L['meadow']] = (230, 230, 200)
        vis = (pal[lab] * 0.6 + ref * 255 * 0.4).astype(np.uint8)
        Image.fromarray(vis).resize((469, 839), Image.NEAREST).save(sys.argv[2])
