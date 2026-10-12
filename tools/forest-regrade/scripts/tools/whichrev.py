"""whichrev.py IOS.png DATADIR MODEL.png : shapes whose visible edges show reversed AA, with cumulative counts."""
import sys, numpy as np
from PIL import Image
from pbart import load
from art import flatten, rasterize
from score import DS, DOX, DEV
png, d, mp = sys.argv[1:4]
sh = load(d)
top = np.full((DEV[1], DEV[0]), -1, np.int32); topc = np.zeros((DEV[1], DEV[0]), np.float32)
for k, s in enumerate(sh):
    r = rasterize(flatten(s.subs, DS), DS, DOX, 0, DEV[0], DEV[1], 16)
    if r is None: continue
    x0, y0, c = r; sl = (slice(y0, y0 + c.shape[0]), slice(x0, x0 + c.shape[1]))
    m = c > 0.02; top[sl][m] = k; topc[sl][m] = c[m]
a = np.asarray(Image.open(png).convert('RGB')).astype(np.int16); b = np.asarray(Image.open(mp).convert('RGB')).astype(np.int16)
dd = np.abs(a - b).max(-1)
edge = (topc > 0.1) & (topc < 0.9)
rev = np.bincount(top[edge & (dd > 25)], minlength=len(sh)); tot = np.bincount(top[edge], minlength=len(sh))
segs = np.array([sum(len(u) - 1 for u in s.subs) for s in sh]); cum = np.cumsum(segs) - segs
for k in np.nonzero(rev >= 4)[0]:
    print('#%4d %-10s rev %4d / edge %5d  segs %4d  cumsegs %6d  bbox %s' % (k, sh[k].layer, rev[k], tot[k], segs[k], cum[k], ','.join('%.0f' % v for v in sh[k].box)))
