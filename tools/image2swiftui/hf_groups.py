"""Named layers of the high-fidelity trace, listed back to front (this is the z-order)."""
import numpy as np
from scipy import ndimage as ndi
from colors import to_hsv
import semantic

GROUPS = ['meadow', 'hedge', 'pathEdges', 'path', 'backTrees', 'pines', 'bridge', 'bushes', 'doorBush', 'door',
          'stones', 'fox', 'flowers', 'frontTrees']


def flower_mask(ref):
    H_, S_, V_ = to_hsv(ref)
    petal = (H_ > 47) & (H_ < 68) & (S_ > 0.55) & (V_ > 0.78)
    centre = (H_ > 28) & (H_ <= 47) & (S_ > 0.75) & (V_ > 0.6)
    purple = (H_ > 265) & (H_ < 320) & (S_ > 0.3) & (V_ > 0.45)
    yel = ndi.binary_closing(petal | centre, iterations=1)
    lbl, n = ndi.label(yel)
    keep = np.zeros(n + 1, bool)
    pa = ndi.sum(petal, lbl, range(1, n + 1))
    ca = ndi.sum(centre, lbl, range(1, n + 1))
    keep[1:] = (pa >= 300) & (ca >= 30)
    ym = keep[lbl]
    lbl, n = ndi.label(ndi.binary_closing(purple, iterations=1))
    sz = np.bincount(lbl.ravel())
    keep = sz >= 60
    keep[0] = False
    pm = keep[lbl]
    return ndi.binary_dilation(ym | pm, iterations=1)


def assign(ref, fine, border):
    """Layer index (into GROUPS) of every fine region."""
    old, _ = semantic.group_map(ref, fine, border)
    names = [semantic.GROUPS[g] for g in old]
    fm = flower_mask(ref)
    n = fine.max() + 1
    cnt = np.bincount(fine.ravel(), minlength=n)
    ffrac = np.bincount(fine.ravel(), weights=fm.ravel().astype(float), minlength=n) / np.maximum(cnt, 1)
    return np.array([GROUPS.index('flowers') if ffrac[i] > 0.5 else GROUPS.index(names[i] if names[i] != 'tufts' else 'meadow')
                     for i in range(n)])
