"""Mechanical no-copy check: no generated shape may match an original shape within EPS design units.
Two shapes match when their flattened outlines have a symmetric Hausdorff distance < EPS (translation is NOT removed:
a copied shape placed elsewhere is caught by the translation-free variant below)."""
import numpy as np
from scipy.spatial import cKDTree
from .core import flatten, tbox

EPS = 0.5
MIN_DIAG_MOVED = 8.0   # translation-free test only for shapes whose bbox diagonal >= this (tiny dots are generic)

def outline(s):
    return np.vstack(flatten(s.subs, 4.0))

def hausdorff(A, B):
    ta, tb = cKDTree(A), cKDTree(B)
    return max(tb.query(A)[0].max(), ta.query(B)[0].max())

def check(generated, originals, eps=EPS, translation_free=True):
    """Returns (min distance found, list of matches (gen index, orig index, distance)).
    translation_free: also compare outlines after aligning bounding-box centres (catches moved copies)."""
    O = [(tbox(s), outline(s)) for s in originals]
    sizes = np.array([[b[2] - b[0], b[3] - b[1]] for b, _ in O])
    matches, dmin = [], np.inf
    for i, g in enumerate(generated):
        bg = tbox(g); G = outline(g); sg = np.array([bg[2] - bg[0], bg[3] - bg[1]])
        cg = np.array([(bg[0] + bg[2]) / 2, (bg[1] + bg[3]) / 2])
        cand = np.nonzero(np.all(np.abs(sizes - sg) < eps * 2 + 1e-9, axis=1))[0]
        for j in cand:
            b, Oj = O[j]
            co = np.array([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2])
            d = hausdorff(G, Oj)
            if translation_free and np.hypot(*sg) >= MIN_DIAG_MOVED: d = min(d, hausdorff(G - cg, Oj - co))
            dmin = min(dmin, d)
            if d < eps: matches.append((i, j, float(d)))
    return float(dmin), matches
