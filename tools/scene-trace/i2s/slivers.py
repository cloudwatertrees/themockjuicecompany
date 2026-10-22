"""Dissolve anti-aliasing slivers before tracing.

A sliver is a small region with almost no interior (nearly every pixel touches another region) whose mean colour lies
on the line between its two main neighbours' colours: the soft 1-2 px ramp the painting has along a hard edge (spot
against cap, cap against grass). Traced as its own shape it gives a thin band with a wobbly outline on both sides.
Each sliver pixel is handed to the neighbouring region whose affine colour model fits it best, so the edge becomes one
boundary that superres.py then places at sub-pixel precision. Thin regions darker or lighter than both neighbours
(strokes, highlights, line art) are not between their neighbours and are kept."""
import numpy as np
from scipy import ndimage as ndi
from superres import affine_models
from regions import SCALE


def dissolve(lab, grp, ref, max_interior=0.2, max_area=600, min_jump=18.0, max_off=0.35):
    H, W = lab.shape
    n = lab.max() + 1
    area = np.bincount(lab.ravel(), minlength=n)
    p = np.pad(lab, 1, mode='edge')
    same = (p[1:-1, :-2] == lab) & (p[1:-1, 2:] == lab) & (p[:-2, 1:-1] == lab) & (p[2:, 1:-1] == lab)
    interior = np.bincount(lab.ravel(), weights=same.ravel().astype(float), minlength=n)
    mean = np.stack([np.bincount(lab.ravel(), weights=ref[..., c].ravel(), minlength=n) for c in range(3)], 1) / np.maximum(area, 1)[:, None]
    # contact counts between regions
    pairs = np.concatenate([np.stack([lab[:, :-1].ravel(), lab[:, 1:].ravel()], 1), np.stack([lab[:-1].ravel(), lab[1:].ravel()], 1)])
    pairs = pairs[pairs[:, 0] != pairs[:, 1]]
    pairs = np.sort(pairs, 1)
    u, cnt = np.unique(pairs, axis=0, return_counts=True)
    nbrs = [[] for _ in range(n)]
    for (a, b), c in zip(u, cnt):
        nbrs[a].append((c, b)); nbrs[b].append((c, a))
    cand = (area <= max_area) & (interior <= max_interior * np.maximum(area, 1))
    sliver = np.zeros(n, bool)
    for r in np.nonzero(cand)[0]:
        nb = sorted(nbrs[r], reverse=True)
        nb = [b for c, b in nb if not cand[b]][:2] or [b for c, b in sorted(nbrs[r], reverse=True)][:2]
        if len(nb) < 2:
            continue
        a, b = mean[nb[0]], mean[nb[1]]
        d = b - a
        L = np.linalg.norm(d)
        if L < min_jump:
            continue
        t = np.dot(mean[r] - a, d) / (L * L)
        off = np.linalg.norm(mean[r] - (a + t * d)) / L
        if 0.05 < t < 0.95 and off < max_off:
            sliver[r] = True
    if not sliver.any():
        return lab, grp, 0
    TH = affine_models(lab, ref)
    out = lab.copy()
    objs = ndi.find_objects(lab + 1)
    OX, OY = W / 2, H / 2
    for r in np.nonzero(sliver)[0]:
        sl = objs[r]
        if sl is None:
            continue
        nb = [b for c, b in sorted(nbrs[r], reverse=True) if not sliver[b]][:4]
        if not nb:
            continue
        ys, xs = np.nonzero(lab[sl] == r)
        ys = ys + sl[0].start; xs = xs + sl[1].start
        xn = (xs + 0.5 - OX) / SCALE; yn = (ys + 0.5 - OY) / SCALE
        T = TH[nb]                                         # k x 3 x 3
        col = T[None, :, 0, :] + T[None, :, 1, :] * xn[:, None, None] + T[None, :, 2, :] * yn[:, None, None]
        err = ((col - ref[ys, xs][:, None, :]) ** 2).sum(-1)
        out[ys, xs] = np.asarray(nb)[err.argmin(1)]
    uu, inv = np.unique(out, return_inverse=True)
    return inv.reshape(out.shape), np.asarray(grp)[uu], int(sliver.sum())
