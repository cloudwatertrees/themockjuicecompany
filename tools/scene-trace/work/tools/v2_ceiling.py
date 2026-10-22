"""v2: score ceiling of a region partition. Each region is filled with the reference smoothed within that region only
(normalised Gaussian convolution, so no colour crosses a boundary), which is the best a smooth fill on this exact
partition can do, with 1x hard edges. Shows whether fills or the partition limit the score.
usage: v2_ceiling.py REG.npy [sigma ...]   (run from the working copy's tools/)"""
import sys, numpy as np
from scipy import ndimage as ndi
from quick import REF, score

reg = np.load(sys.argv[1])
for s in [float(a) for a in sys.argv[2:]] or [1.0, 2.0, 4.0]:
    out = np.zeros_like(REF)
    for sl, r in zip(ndi.find_objects(reg + 1), range(reg.max() + 1)):
        if sl is None: continue
        sl = tuple(slice(max(0, a.start - 12), a.stop + 12) for a in sl)
        m = (reg[sl] == r).astype(float)
        w = ndi.gaussian_filter(m, s)
        for c in range(3):
            v = ndi.gaussian_filter(REF[sl][..., c] * m, s) / np.maximum(w, 1e-9)
            out[sl][..., c][m > 0] = v[m > 0]
    print('sigma %.1f: SSIM %.4f dE %.3f p95 %.2f | lp dE %.3f p95 %.2f max %.1f' % ((s,) + score(out)))
