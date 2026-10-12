"""Merge SOFT-boundary region pairs (same layer) when one fine bilinear mesh fits the union as well as two separate
meshes fit the parts (incl. the transition band): soft shadows/light pools become smooth mesh ramps, while distinct
shapes (pebbles, rims, small objects) that a mesh cannot draw stay separate regions."""
import sys, numpy as np
from scipy import ndimage as ndi
from PIL import Image
from skimage.color import rgb2lab
from regions import UF
from meshfit import grid_dims, fit, bilinear_weights
from pb_bounds import classify, SOFT
from art import W, H
SP = '/tmp/work/'

def mesh_rms(X, Y, C, box, h=6.0, nmax=96):
    nx, ny = grid_dims(box[2] - box[0], box[3] - box[1], h)
    nx, ny = min(nx, nmax), min(ny, nmax)
    V = fit(X, Y, C, box, nx, ny, lam=0.01)
    R = bilinear_weights(X, Y, box, nx, ny) @ V - C
    return np.sqrt((R ** 2).sum(1)), V

def run(src, dst, tol=0.35, band_tol=2.5, max_union=400000):
    reg = np.load(src + '_reg.npy'); lay = np.load(src + '_layer.npy'); P = np.load(src + '_pairs.npy')
    rl = rgb2lab(np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255)
    n = reg.max() + 1
    area = np.bincount(reg.ravel(), minlength=n)
    objs = ndi.find_objects(reg + 1)
    ys, xs = np.mgrid[0:H, 0:W]
    # pixels adjacent to a third region are excluded from the fits (AA with other neighbours)
    soft = [(int(a), int(b), cnt) for a, b, c, cnt, *_ in P if int(c) == SOFT and lay[int(a)] == lay[int(b)]]
    soft.sort(key=lambda t: -t[2])
    uf = UF(n); merged = 0; tried = 0
    for a, b, cnt in soft:
        if cnt < 6: continue
        ra, rb = uf.f(a), uf.f(b)
        if ra == rb: continue
        # current members of each union
        if area[a] + area[b] > max_union: continue
        sa, sb = objs[a], objs[b]
        y0 = min(sa[0].start, sb[0].start); y1 = max(sa[0].stop, sb[0].stop)
        x0 = min(sa[1].start, sb[1].start); x1 = max(sa[1].stop, sb[1].stop)
        sub = reg[y0:y1, x0:x1]
        ma, mb = sub == a, sub == b
        other = ~(ma | mb)
        clean = ~ndi.binary_dilation(other, iterations=1)
        tried += 1
        def pts(m):
            yy, xx = np.nonzero(m & clean)
            return xx + x0 + 0.5, yy + y0 + 0.5, rl[y0:y1, x0:x1][m & clean]
        Xa, Ya, Ca = pts(ma); Xb, Yb, Cb = pts(mb)
        if len(Ca) < 20 or len(Cb) < 20: continue
        boxa = (sa[1].start, sa[0].start, sa[1].stop, sa[0].stop); boxb = (sb[1].start, sb[0].start, sb[1].stop, sb[0].stop)
        resa, _ = mesh_rms(Xa, Ya, Ca, boxa); resb, _ = mesh_rms(Xb, Yb, Cb, boxb)
        Xu, Yu, Cu = np.concatenate([Xa, Xb]), np.concatenate([Ya, Yb]), np.concatenate([Ca, Cb])
        resu, _ = mesh_rms(Xu, Yu, Cu, (x0, y0, x1, y1))
        # transition band: union pixels within 2 px of the a|b boundary
        bnd = (ndi.binary_dilation(ma, iterations=2) & mb) | (ndi.binary_dilation(mb, iterations=2) & ma)
        inb = np.concatenate([bnd[(ma & clean)], bnd[(mb & clean)]])
        sep = np.sqrt((np.concatenate([resa, resb]) ** 2).mean()); uni = np.sqrt((resu ** 2).mean())
        band = resu[inb].mean() if inb.any() else 0
        if uni <= sep + tol and band <= band_tol:
            uf.u(a, b); merged += 1
    root = np.array([uf.f(i) for i in range(n)])
    ur, reg2 = np.unique(root[reg], return_inverse=True); reg2 = reg2.reshape(reg.shape)
    lay2 = lay[ur]
    P2 = classify(reg2, rl)
    np.save(dst + '_reg.npy', reg2.astype(np.int32)); np.save(dst + '_layer.npy', lay2.astype(np.int16)); np.save(dst + '_pairs.npy', P2)
    print('soft pairs tried %d, merged %d; regions %d -> %d' % (tried, merged, n, reg2.max() + 1))

if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
