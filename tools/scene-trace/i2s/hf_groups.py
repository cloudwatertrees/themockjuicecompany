"""Named layers for the A/B home-screen scenes, assigned automatically from colour classes (no hand-placed regions).
Listed back to front (this is the z-order). Adapted from the forest version (semantic.py ROI table x colour class)."""
import numpy as np
from scipy import ndimage as ndi
from colors import to_lab, to_hsv
from masks import path_mask, border_mask, PX

GROUPS = ['meadow', 'pathEdges', 'path', 'water', 'rocks', 'wood', 'foliage', 'conifers', 'accents', 'flowers']


def flower_mask(ref):
    """Daisies (white petals with a yellow centre), purple and yellow flowers: small compact colour blobs."""
    h, s, v = to_hsv(ref)
    lab = to_lab(ref)
    purple = (h > 260) & (h < 325) & (s > 0.25) & (v > 0.45)
    yellow = (h > 40) & (h < 62) & (s > 0.45) & (v > 0.8)
    white = (lab[..., 0] > 88) & (np.hypot(lab[..., 1], lab[..., 2]) < 12)
    m = ndi.binary_closing(purple | yellow | white, iterations=1)
    lbl, n = ndi.label(m)
    keep = np.zeros(n + 1, bool)
    for i, sl in enumerate(ndi.find_objects(lbl), 1):
        comp = lbl[sl] == i
        a = comp.sum()
        if a < 40 * PX * PX or a > 4000 * PX * PX:
            continue
        fy = (yellow[sl] & comp).sum() / a
        fp = (purple[sl] & comp).sum() / a
        fw = (white[sl] & comp).sum() / a
        if fp > 0.5 or (fy > 0.08 and fw > 0.3) or fy > 0.6:
            keep[i] = True
    return ndi.binary_dilation(keep[lbl], iterations=round(PX))


def classify(L, a, b):
    hue = np.degrees(np.arctan2(b, a)) % 360
    chroma = np.hypot(a, b)
    if a > 22 and L < 75:
        return 'accents'                      # red mushroom caps, lantern glow
    if b < -9 and a < -2 and L > 55 and np.hypot(a, b) > 14:
        return 'water'
    if chroma < 14 and b < 4 and 40 < L < 90:
        return 'rocks'                        # lavender-grey stone
    if a > 4 and b > 8 and L < 72:
        return 'wood'
    if a < -3 or (90 < hue < 200 and chroma > 10):
        if L < 52 and hue > 140:
            return 'conifers'
        if L < 72:
            return 'foliage'
        return 'meadow'
    return 'meadow'


def assign(ref, fine, border):
    """Layer index (into GROUPS) of every fine region."""
    lab = to_lab(ref)
    n = fine.max() + 1
    f = fine.ravel()
    cnt = np.maximum(np.bincount(f, minlength=n), 1).astype(float)
    mean = np.stack([np.bincount(f, weights=lab[..., k].ravel(), minlength=n) for k in range(3)], 1) / cnt[:, None]
    frac = lambda m: np.bincount(f, weights=m.ravel().astype(float), minlength=n) / cnt
    pf, bf, ff = frac(path_mask(ref)), frac(border), frac(flower_mask(ref))
    G = {g: i for i, g in enumerate(GROUPS)}
    out = np.zeros(n, int)
    for i in range(n):
        if ff[i] > 0.5:
            g = 'flowers'
        elif pf[i] > 0.5:
            g = 'path'
        elif bf[i] > 0.5:
            g = 'pathEdges'
        else:
            g = classify(*mean[i])
        out[i] = G[g]
    return out
