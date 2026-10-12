"""inv396.py IOS.png DATADIR TARGET_INDEX_IN_DATADIR : reversed-AA px along the target's outline (where it is topmost)."""
import sys, numpy as np
from PIL import Image
from pbart import load
from art import flatten, rasterize
from pbrender import render
from score import DS, DOX, DEV
png, d, t = sys.argv[1], sys.argv[2], int(sys.argv[3])
sh = load(d); s = sh[t]
x0, y0, c = rasterize(flatten(s.subs, DS), DS, DOX, 0, DEV[0], DEV[1], 16)
h, w = c.shape
m = render(sh, DS, DOX - x0, -y0, w, h)          # model of the whole scene over the target's box
m = (np.clip(m, 0, 1) * 255 + .5).astype(int)
cov_above = np.zeros((h, w))
for u in sh[t + 1:]:
    r = rasterize(flatten(u.subs, DS), DS, DOX - x0, -y0, w, h, 16)
    if r is None: continue
    a0, b0, cc = r; cov_above[b0:b0 + cc.shape[0], a0:a0 + cc.shape[1]] = np.maximum(cov_above[b0:b0 + cc.shape[0], a0:a0 + cc.shape[1]], cc)
i = np.asarray(Image.open(png).convert('RGB')).astype(int)[y0:y0 + h, x0:x0 + w]
dd = np.abs(i - m).max(-1)
edge = (c > 0.1) & (c < 0.9) & (cov_above < 0.02)
print('target edge px %d  reversed(>25) %d' % (edge.sum(), (edge & (dd > 25)).sum()))
