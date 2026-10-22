"""Phase B stage 2: classify every region boundary (pair) as hard / soft-edge / smooth from the reference."""
import sys, numpy as np
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000
from regions import boundary_pairs
from art import W, H
SP = '/tmp/work/'
HARD, SOFT, SMOOTH = 0, 1, 2

def classify(reg, rl):
    y0, x0, y1, x1 = boundary_pairs(reg)
    a, b = reg[y0, x0], reg[y1, x1]
    dy, dx = y1 - y0, x1 - x0
    def at(y, x): return rl[np.clip(y, 0, H - 1), np.clip(x, 0, W - 1)]
    def de(k): return deltaE_ciede2000(at(y0 - dy * k, x0 - dx * k), at(y1 + dy * k, x1 + dx * k))
    near, mid, far = de(1), de(3), de(6)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    key = lo.astype(np.int64) * (reg.max() + 1) + hi
    uk, inv = np.unique(key, return_inverse=True)
    order = np.argsort(inv, kind='stable'); splits = np.nonzero(np.diff(inv[order]))[0] + 1
    out = []
    for g in np.split(order, splits):
        n_, m_, f_ = np.median(near[g]), np.median(mid[g]), np.median(far[g])
        if n_ >= 3 and n_ >= 0.6 * m_: c = HARD
        elif m_ >= 3 and m_ >= 0.75 * f_: c = SOFT
        else: c = SMOOTH
        out.append((lo[g[0]], hi[g[0]], c, len(g), n_, m_, f_))
    return np.array(out)

if __name__ == '__main__':
    base = sys.argv[1]
    reg = np.load(base + '_reg.npy')
    rl = rgb2lab(np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255)
    P = classify(reg, rl)
    np.save(base + '_pairs.npy', P)
    for c, nm in [(HARD, 'hard'), (SOFT, 'soft-edge'), (SMOOTH, 'smooth')]:
        m = P[:, 2] == c
        print('%-9s pairs %5d  boundary px %6d (%.1f%%)' % (nm, m.sum(), P[m, 3].sum(), 100 * P[m, 3].sum() / P[:, 3].sum()))
