"""Semantic layer map: colour class of each fine region x hand-placed object ROIs.

The ROI polygons below are placed by hand for the 937x1678 forest path illustration.
A different image needs its own ROI table.
"""
import numpy as np
import cv2
from colors import to_lab

GROUPS = ['meadow', 'hedge', 'pathEdges', 'path', 'backTrees', 'pines', 'bridge', 'bushes',
          'doorBush', 'door', 'stones', 'fox', 'tufts', 'frontTrees']
G = {g: i for i, g in enumerate(GROUPS)}

ROI = {
    'hedge': [[(560, 0), (937, 0), (937, 585), (885, 565), (800, 485), (700, 400), (610, 335), (560, 250)]],
    'backTrees': [[(0, 0), (232, 0), (236, 60), (300, 70), (300, 240), (250, 300), (180, 335), (100, 350), (0, 362)],
                  [(0, 362), (118, 368), (125, 485), (0, 495)],
                  [(0, 560), (108, 560), (112, 865), (0, 875)]],
    'pines': [[(380, 388), (425, 388), (500, 560), (498, 672), (318, 672), (318, 560)],
              [(238, 1378), (292, 1378), (362, 1560), (362, 1678), (188, 1678), (188, 1560)]],
    'bridge': [[(92, 688), (180, 676), (300, 658), (392, 662), (442, 718), (482, 860), (478, 952), (330, 962), (258, 946), (150, 852), (92, 852)]],
    'bushes': [[(228, 912), (392, 912), (392, 1062), (228, 1062)],
               [(452, 792), (607, 792), (607, 928), (452, 928)],
               [(228, 0), (378, 0), (378, 72), (300, 72), (228, 62)]],
    'doorBush': [[(638, 556), (937, 556), (937, 945), (900, 965), (760, 965), (648, 905)]],
    'door': [[(745, 668), (906, 668), (906, 896), (745, 896)]],
    'stones': [[(438, 902), (762, 902), (762, 1042), (438, 1042)]],
    'fox': [[(710, 984), (866, 984), (866, 1152), (710, 1152)]],
    'frontTrees': [[(0, 1110), (245, 1110), (245, 1678), (0, 1678)],
                   [(615, 1045), (937, 1045), (937, 1678), (615, 1678)],
                   [(848, 935), (937, 935), (937, 1045), (848, 1045)]],
}


def roi_masks(shape):
    out = {}
    for g, polys in ROI.items():
        m = np.zeros(shape, np.uint8)
        for p in polys:
            cv2.fillPoly(m, [np.array(p, np.int32)], 1)
        out[g] = m.astype(bool)
    return out


def classify(mean_lab):
    L, a, b = mean_lab
    hue = np.degrees(np.arctan2(b, a))
    chroma = np.hypot(a, b)
    if L > 72 and -8 < a < 12 and 4 < b < 40:
        return 'cream'
    if b < -6:
        return 'blue'
    if a > 30 and b > 35:
        return 'orange'
    if a > 6 and L < 70:
        return 'brownish'
    if a < -8 and chroma > 25 and hue < 127 and L > 55:
        return 'meadowGreen'
    if a < -8:
        return 'green'
    return 'other'


def group_map(base, fine, border_mask):
    """Assign each fine region a semantic group."""
    lab = to_lab(base)
    n = fine.max() + 1
    cnt = np.bincount(fine.ravel(), minlength=n).astype(float)
    mean = np.stack([np.bincount(fine.ravel(), weights=lab[..., k].ravel(), minlength=n) for k in range(3)], 1) / np.maximum(cnt, 1)[:, None]
    bfrac = np.bincount(fine.ravel(), weights=border_mask.ravel().astype(float), minlength=n) / np.maximum(cnt, 1)
    R = roi_masks(fine.shape)
    rfrac = {g: np.bincount(fine.ravel(), weights=m.ravel().astype(float), minlength=n) / np.maximum(cnt, 1) for g, m in R.items()}

    def inroi(i, g):
        return rfrac[g][i] > 0.5

    grp = np.zeros(n, int)
    for i in range(n):
        c = classify(mean[i])
        g = 'meadow'
        if inroi(i, 'fox') and c in ('orange', 'cream', 'brownish', 'other'):
            g = 'fox'
        elif inroi(i, 'door') and c in ('brownish', 'orange', 'other'):
            g = 'door'
        elif inroi(i, 'bridge') and c in ('blue', 'brownish', 'other') and bfrac[i] < 0.5:
            g = 'bridge'
        elif inroi(i, 'stones') and c == 'blue':
            g = 'stones'
        elif c == 'cream':
            g = 'path'
        elif bfrac[i] > 0.5 and c in ('brownish', 'other', 'cream'):
            g = 'pathEdges'
        elif c in ('green', 'meadowGreen', 'other', 'blue'):
            for cand in ('door', 'bridge', 'pines', 'bushes', 'doorBush', 'hedge', 'backTrees', 'frontTrees'):
                if inroi(i, cand) and (c in ('green', 'other', 'blue') or cand == 'pines'):
                    g = cand if cand not in ('door',) else 'doorBush'
                    break
        grp[i] = G[g]
    return grp, mean
