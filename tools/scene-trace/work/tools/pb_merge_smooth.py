"""Merge regions across SMOOTH boundaries (same layer), reclassify, and pick a mesh cell size per region by residual."""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2lab
from regions import UF
from pb_bounds import classify, SMOOTH
from meshfit import grid_dims, fit, bilinear_weights
from art import W, H
SP = '/Users/laverath/Desktop/themockjuicecompany/tools/scene-trace/work/'

def choose_cells(reg, rl, hs=(24, 16, 11, 8, 6), nmax=64):
    n = reg.max() + 1
    e = np.zeros_like(reg, bool)
    e[:, 1:] |= reg[:, 1:] != reg[:, :-1]; e[:, :-1] |= reg[:, 1:] != reg[:, :-1]
    e[1:] |= reg[1:] != reg[:-1]; e[:-1] |= reg[1:] != reg[:-1]
    ys, xs = np.mgrid[0:H, 0:W]
    objs = ndi.find_objects(reg + 1); cell = np.full(n, float(hs[0])); rms_out = np.zeros(n)
    for r in range(n):
        sl = objs[r]
        if sl is None: continue
        m = (reg[sl] == r) & ~e[sl]
        if m.sum() < 60: continue
        X, Y, C = xs[sl][m] + 0.5, ys[sl][m] + 0.5, rl[sl][m]
        box = (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop)
        res = []
        for h in hs:
            nx, ny = grid_dims(box[2] - box[0], box[3] - box[1], h)
            if nx > nmax or ny > nmax: res.append(np.inf); continue
            V = fit(X, Y, C, box, nx, ny)
            res.append(np.sqrt(((bilinear_weights(X, Y, box, nx, ny) @ V - C) ** 2).sum(1).mean()))
        res = np.array(res); best = res.min()
        ok = np.nonzero(res <= best + 0.06)[0]
        cell[r] = hs[ok[0]]; rms_out[r] = res[ok[0]]
        if m.sum() > 5000: cell[r] = min(cell[r], 16)
        if m.sum() > 40000: cell[r] = min(cell[r], 11)
    return cell, rms_out

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    reg = np.load(src + '_reg.npy'); lay = np.load(src + '_layer.npy'); P = np.load(src + '_pairs.npy')
    uf = UF(reg.max() + 1)
    for a, b, c, *_ in P:
        if int(c) == SMOOTH and lay[int(a)] == lay[int(b)]: uf.u(int(a), int(b))
    root = np.array([uf.f(i) for i in range(reg.max() + 1)])
    ur, reg2 = np.unique(root[reg], return_inverse=True); reg2 = reg2.reshape(reg.shape)
    lay2 = lay[ur]
    rl = rgb2lab(np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255)
    P2 = classify(reg2, rl)
    cell, rms = choose_cells(reg2, rl)
    np.save(dst + '_reg.npy', reg2.astype(np.int32)); np.save(dst + '_layer.npy', lay2.astype(np.int16))
    np.save(dst + '_pairs.npy', P2); np.save(dst + '_cell.npy', cell)
    print('regions %d -> %d; cells:' % (reg.max() + 1, reg2.max() + 1), dict(zip(*np.unique(cell, return_counts=True))))
    for c, nm in [(0, 'hard'), (1, 'soft'), (2, 'smooth')]:
        m = P2[:, 2] == c; print('  %s pairs %d px %d' % (nm, m.sum(), P2[m, 3].sum()))
