"""Phase B region extraction from Phase A geometry: visible-shape label map -> merge across non-hard boundaries
(same layer only) -> regions. Boundary hardness from the reference."""
import sys, numpy as np
from scipy import ndimage as ndi
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000
import model
from art import load, LAYERS, W, H
SP = '/tmp/work/'

def shape_labels(shapes):
    """Per pixel (1x canvas): index of the shape with the largest visible weight."""
    covs = model.coverage(shapes); vis, _ = model.visible(covs)
    best = np.zeros((model.HX, model.WX)); lab = np.full((model.HX, model.WX), -1, np.int32)
    for i, v in enumerate(vis):
        if v is None: continue
        x0, y0, w = v; h, ww = w.shape
        sub = best[y0:y0 + h, x0:x0 + ww]; m = w > sub
        sub[m] = w[m]; lab[y0:y0 + h, x0:x0 + ww][m] = i
    M = model.M
    return lab[M:M + H, M:M + W]

class UF:
    def __init__(s, n): s.p = np.arange(n)
    def f(s, a):
        while s.p[a] != a:
            s.p[a] = s.p[s.p[a]]; a = s.p[a]
        return a
    def u(s, a, b):
        a, b = s.f(a), s.f(b)
        if a != b: s.p[max(a, b)] = min(a, b)

def boundary_pairs(lab):
    """All 4-neighbour pixel pairs with different labels: (y0,x0,y1,x1) arrays."""
    out = []
    a, b = lab[:, :-1], lab[:, 1:]; ys, xs = np.nonzero(a != b); out.append((ys, xs, ys, xs + 1))
    a, b = lab[:-1], lab[1:]; ys, xs = np.nonzero(a != b); out.append((ys, xs, ys + 1, xs))
    return [np.concatenate(t) for t in zip(*out)]

def hardness(ref_lab, y0, x0, y1, x1, d=1):
    """dE00 across each boundary pair over a 1+2d px span, and over a 1+2*(d+2) px span (ratio test)."""
    dy, dx = y1 - y0, x1 - x0
    def at(y, x):
        return ref_lab[np.clip(y, 0, H - 1), np.clip(x, 0, W - 1)]
    near = deltaE_ciede2000(at(y0 - dy * d, x0 - dx * d), at(y1 + dy * d, x1 + dx * d))
    far = deltaE_ciede2000(at(y0 - dy * (d + 2), x0 - dx * (d + 2)), at(y1 + dy * (d + 2), x1 + dx * (d + 2)))
    return near, far

if __name__ == '__main__':
    src = sys.argv[1]
    shapes = load(src)
    lab = shape_labels(shapes)
    np.save(SP + 'out/B_shapelab.npy', lab)
    ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
    rl = rgb2lab(ref)
    y0, x0, y1, x1 = boundary_pairs(lab)
    a, b = lab[y0, x0], lab[y1, x1]
    near, far = hardness(rl, y0, x0, y1, x1)
    # aggregate per label pair
    key = np.minimum(a, b).astype(np.int64) * 100000 + np.maximum(a, b)
    uk, inv = np.unique(key, return_inverse=True)
    med_near = np.array([np.median(near[inv == k]) for k in range(len(uk))]) if len(uk) < 2000 else None
    order = np.argsort(inv); inv_s = inv[order]; splits = np.nonzero(np.diff(inv_s))[0] + 1
    groups = np.split(order, splits)
    stats = np.array([(np.median(near[g]), np.median(far[g]), len(g)) for g in groups])
    np.save(SP + 'out/B_pairs.npy', np.concatenate([np.stack([uk // 100000, uk % 100000], 1), stats], 1))
    print('shapes', len(shapes), 'visible labels', len(np.unique(lab)), 'adjacent pairs', len(uk))
    for t in (2, 3, 4, 6):
        hard = (stats[:, 0] >= t) & (stats[:, 0] >= 0.6 * stats[:, 1])
        print('tau %d: hard pairs %d (%.1f%% of boundary px)' % (t, hard.sum(), 100 * stats[hard, 2].sum() / stats[:, 2].sum()))
