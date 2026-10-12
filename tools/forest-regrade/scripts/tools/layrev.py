"""layrev.py PREFIX DATADIR : per-layer render vs per-layer model; reversed-edge shapes with in-layer cumulative counts."""
import sys, numpy as np
from PIL import Image
from pbart import load
from art import flatten, rasterize, LAYERS
from pbrender import composite_one
from score import DS, DOX, DEV
pre, d = sys.argv[1], sys.argv[2]
sh = load(d)
for L in LAYERS:
    ss = [s for s in sh if s.layer == L]
    im = np.asarray(Image.open(pre + '_' + L + '.png').convert('RGBA')).astype(np.float64) / 255
    # model: layer alone over transparent -> compare premultiplied colour
    col = np.zeros((DEV[1], DEV[0], 3)); al = np.zeros((DEV[1], DEV[0]))
    top = np.full((DEV[1], DEV[0]), -1, np.int32); topc = np.zeros((DEV[1], DEV[0]), np.float32)
    for k, s in enumerate(ss):
        r = rasterize(flatten(s.subs, DS), DS, DOX, 0, DEV[0], DEV[1], 16)
        if r is None: continue
        composite_one(col, al, s, r, DS, DOX, 0)
        x0, y0, c = r; sl = (slice(y0, y0 + c.shape[0]), slice(x0, x0 + c.shape[1])); m = c > 0.02
        top[sl][m] = k; topc[sl][m] = c[m]
    got = im[..., :3] * im[..., 3:4]
    dd = np.abs(got - col).max(-1) * 255
    edge = (topc > 0.1) & (topc < 0.9)
    rev = np.bincount(top[edge & (dd > 25)], minlength=len(ss))
    segs = np.array([sum(len(u) - 1 for u in s.subs) for s in ss]); cum = np.cumsum(segs) - segs
    bad = np.nonzero(rev >= 4)[0]
    print('%-10s draws %4d segs %5d  reversed shapes: %s' % (L, len(ss), segs.sum(), ', '.join('#%d(rev %d, cumsegs %d, segs %d)' % (k, rev[k], cum[k], segs[k]) for k in bad)))
