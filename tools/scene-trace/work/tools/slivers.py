"""Dissolve anti-aliasing slivers and specks: thin/small regions whose colour lies between their neighbours
are re-assigned pixel-wise to the neighbour whose local colour model fits best. Real thin lines are kept."""
import sys, numpy as np
from scipy import ndimage as ndi
from PIL import Image
from skimage.color import rgb2lab
from merge import basis
from art import W, H
SP = '/Users/laverath/Desktop/themockjuicecompany/tools/scene-trace/work/'

def fit_models(reg, rl, deg=2, erode=1):
    """Per-region polynomial colour model (Lab), fitted on eroded interiors (falls back to all pixels)."""
    n = reg.max() + 1
    ys, xs = np.mgrid[0:H, 0:W]
    inner = np.ones_like(reg, bool)
    if erode:
        e = np.zeros_like(reg, bool)
        e[:, 1:] |= reg[:, 1:] != reg[:, :-1]; e[:, :-1] |= reg[:, 1:] != reg[:, :-1]
        e[1:] |= reg[1:] != reg[:-1]; e[:-1] |= reg[1:] != reg[:-1]
        inner = ~e
    objs = ndi.find_objects(reg + 1)
    models = [None] * n
    for r in range(n):
        sl = objs[r]
        if sl is None: continue
        m = reg[sl] == r
        mi = m & inner[sl]
        if mi.sum() >= 6: m = mi
        yy, xx = ys[sl][m] + 0.5, xs[sl][m] + 0.5
        c = rl[sl][m]
        k = basis(xx, yy, deg).shape[1]
        d = deg if len(c) >= 3 * k else (1 if len(c) >= 9 else 0)
        Phi = basis(xx, yy, d)
        coef, *_ = np.linalg.lstsq(Phi, c, rcond=None)
        models[r] = (d, coef)
    return models

def evalm(model, xs, ys):
    d, coef = model
    return basis(xs, ys, d) @ coef

def dissolve(reg, rl, models, thin_px=1.0, speck=6, between_tol=4.0, band_px=2.5):
    n = reg.max() + 1
    dt = ndi.distance_transform_edt(np.ones_like(reg, bool))  # placeholder shape
    objs = ndi.find_objects(reg + 1)
    sizes = np.bincount(reg.ravel(), minlength=n)
    out = reg.copy(); nd = 0; kept_lines = 0
    for r in range(n):
        sl = objs[r]
        if sl is None or models[r] is None: continue
        y0, y1 = max(sl[0].start - 2, 0), min(sl[0].stop + 2, H); x0, x1 = max(sl[1].start - 2, 0), min(sl[1].stop + 2, W)
        sub = reg[y0:y1, x0:x1]; m = sub == r
        thick = ndi.distance_transform_edt(np.pad(m, 1))[1:-1, 1:-1].max()
        if thick > band_px + 0.01 and sizes[r] > speck: continue
        wide = thick > thin_px + 0.01 and sizes[r] > speck      # 1..2.5 px bands: only strictly in-between colours
        ring = ndi.binary_dilation(m, iterations=1) & ~m
        nbrs, counts = np.unique(sub[ring], return_counts=True)
        if len(nbrs) == 0: continue
        ys, xs = np.nonzero(m); X, Y = xs + x0 + 0.5, ys + y0 + 0.5
        cs = rl[y0:y1, x0:x1][m].mean(0)
        order = np.argsort(-counts)
        if len(nbrs) >= 2:
            A, B = nbrs[order[0]], nbrs[order[1]]
            ca, cb = evalm(models[A], X, Y).mean(0), evalm(models[B], X, Y).mean(0)
            v = cb - ca; t_raw = (cs - ca) @ v / max(v @ v, 1e-9); t = np.clip(t_raw, 0, 1)
            dperp = np.linalg.norm(cs - (ca + t * v))
            near_side = min(np.linalg.norm(cs - ca), np.linalg.norm(cs - cb))
            is_between = (0.05 < t_raw < 0.95 and dperp < between_tol) or near_side < 1.5
            if wide: is_between = 0.1 < t_raw < 0.9 and dperp < between_tol
        else:
            if wide: continue
            A = nbrs[0]; ca = evalm(models[A], X, Y).mean(0)
            is_between = np.linalg.norm(cs - ca) < between_tol
        if not is_between:
            kept_lines += 1; continue
        # pixel-wise reassignment to the best-fitting neighbour model
        cand = [c for c in nbrs if models[c] is not None]
        if not cand: continue
        costs = np.stack([np.linalg.norm(rl[y0:y1, x0:x1][m] - evalm(models[c], X, Y), axis=1) for c in cand], 1)
        out[y0:y1, x0:x1][m] = np.array(cand)[costs.argmin(1)]
        nd += 1
    return out, nd, kept_lines

if __name__ == '__main__':
    reg = np.load(sys.argv[1]); out = sys.argv[2]
    ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
    rl = rgb2lab(ref)
    for it in range(2):
        models = fit_models(reg, rl)
        reg, nd, kl = dissolve(reg, rl, models)
        ur, reg = np.unique(reg, return_inverse=True); reg = reg.reshape((H, W))
        print('pass %d: dissolved %d, kept thin lines %d, regions now %d' % (it, nd, kl, len(ur)))
    np.save(out, reg)
