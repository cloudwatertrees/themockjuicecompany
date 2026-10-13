"""Tone regions of a rendered object and the fit objective shared by every element type.
Classes (fixed thresholds, identical for original and generated): 0 none, 1 pale (halo/ground/flowers: a* > -15),
2 dark foliage (L* <= 62), 3 mid foliage (62 < L* <= 71), 4 light foliage (L* > 71)."""
import numpy as np
from skimage import measure
from fe.core import rgb2lab, render_box

THR = dict(a_pale=-15.0, dark=62.0, mid=71.0)

def classes(img, al):
    lab = rgb2lab(img)
    c = np.zeros(al.shape, np.int8)
    on = al > 0.5
    pale = on & (lab[..., 1] > THR['a_pale'])
    fol = on & ~pale
    c[pale] = 1
    c[fol & (lab[..., 0] <= THR['dark'])] = 2
    c[fol & (lab[..., 0] > THR['dark']) & (lab[..., 0] <= THR['mid'])] = 3
    c[fol & (lab[..., 0] > THR['mid'])] = 4
    return c

def render_classes(shapes, box, scale):
    img, al = render_box(shapes, box, scale)
    # composite over white so un-premultiplied colour is exact where al == 1
    return classes(img + (1 - al[..., None]), al)

def curvature_hist(mask, scale, bins=np.linspace(0, 1.2, 13)):
    """Histogram of |turning| per unit length along the mask's contours (outline-curvature signature), plus
    contour length in units."""
    if mask.sum() < 4: return np.zeros(len(bins) - 1), 0.0
    k_all, w_all = [], []
    for C in measure.find_contours(np.pad(mask.astype(float), 1), 0.5):
        C = C / scale
        if len(C) < 8: continue
        # resample at 1 unit
        d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
        if d[-1] < 6: continue
        t = np.arange(0, d[-1], 1.0); P = np.c_[np.interp(t, d, C[:, 0]), np.interp(t, d, C[:, 1])]
        T = np.diff(P, axis=0); a = np.arctan2(T[:, 0], T[:, 1])
        da = np.abs((np.diff(a) + np.pi) % (2 * np.pi) - np.pi)
        # smooth over 3 units (traced outline scale)
        da = np.convolve(da, np.ones(3) / 3, mode='same')
        k_all.append(da); w_all.append(np.ones_like(da))
    if not k_all: return np.zeros(len(bins) - 1), 0.0
    k = np.concatenate(k_all)
    h, _ = np.histogram(np.clip(k, 0, bins[-1] - 1e-6), bins); return h / max(h.sum(), 1), float(len(k))

def objective(cg, co, scale, w_curv=0.5, classes_used=(1, 2, 3, 4), weights=None):
    """1 - IoU per tone class (weighted by the original class area) + w_curv * L1 distance of curvature histograms
    + contour-length ratio penalty. Returns (total, per-class dict)."""
    tot, per = 0.0, {}
    area_o = {c: (co == c).sum() for c in classes_used}; A = sum(area_o.values())
    for c in classes_used:
        g, o = cg == c, co == c
        inter = (g & o).sum(); uni = (g | o).sum()
        iou = inter / uni if uni else 1.0
        hg, lg = curvature_hist(g, scale); ho, lo = curvature_hist(o, scale)
        cd = float(np.abs(hg - ho).sum()) if lo > 0 else 0.0
        lr = abs(np.log((lg + 1) / (lo + 1)))
        w = (weights or {}).get(c, area_o[c] / A)
        per[c] = dict(iou=round(float(iou), 3), curv=round(cd, 3), len_ratio=round(float(np.exp(lr)), 2))
        tot += w * ((1 - iou) + w_curv * (cd + 0.5 * lr))
    return tot, per

def soft_objective(cg, co, scale, w_curv=0.5, classes_used=(1, 2, 3, 4), sigmas=(8.0, 3.0)):
    """Smooth version used for optimisation: per class, L1 distance between Gaussian-blurred one-hot masks (multi-scale,
    normalised by the original class area) + w_curv * curvature-histogram distance. Hard IoU reported alongside."""
    from scipy import ndimage as ndi
    tot, per = 0.0, {}
    area_o = {c: max((co == c).sum(), 1) for c in classes_used}; A = sum(area_o.values())
    for c in classes_used:
        g, o = (cg == c).astype(float), (co == c).astype(float)
        d = 0.0
        for s in sigmas:
            d += np.abs(ndi.gaussian_filter(g, s * scale) - ndi.gaussian_filter(o, s * scale)).sum() / area_o[c] / len(sigmas)
        hg, lg = curvature_hist(g > 0.5, scale); ho, lo = curvature_hist(o > 0.5, scale)
        cd = float(np.abs(hg - ho).sum()) if lo > 0 else 0.0
        inter = ((g > 0.5) & (o > 0.5)).sum(); uni = ((g > 0.5) | (o > 0.5)).sum()
        per[c] = dict(iou=round(float(inter / uni if uni else 1), 3), soft=round(float(d), 3), curv=round(cd, 3))
        tot += area_o[c] / A * (d + w_curv * cd)
    return tot, per
