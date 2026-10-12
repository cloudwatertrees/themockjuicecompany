"""prune.py SRC DST : drop shapes whose visible coverage in the final composite is negligible (< 0.5 px at 1x
and < 0.02 of their own coverage), checked at 3x supersampling. The first shape (the full-canvas base that fills
antialiasing gaps between neighbouring shapes) is always kept."""
import sys, numpy as np
from pbart import load, write
from art import flatten, rasterize, W, H
src, dst = sys.argv[1], sys.argv[2]
sh = load(src); S = 3
covs = [rasterize(flatten(s.subs, S), S, 0, 0, W * S, H * S, 4) for s in sh]
T = np.ones((H * S, W * S), np.float32); keep = [False] * len(sh)
for i in range(len(sh) - 1, -1, -1):
    r = covs[i]
    if r is None: continue
    x0, y0, c = r; h, w = c.shape
    v = (c * T[y0:y0 + h, x0:x0 + w]).sum() / S / S
    keep[i] = v >= 0.5 or v >= 0.02 * c.sum() / S / S
    T[y0:y0 + h, x0:x0 + w] *= (1 - c)
keep[0] = True
out = [s for s, k in zip(sh, keep) if k]
print('kept %d of %d shapes' % (len(out), len(sh)))
write(out, dst)
