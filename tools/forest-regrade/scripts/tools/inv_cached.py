"""inv_cached.py prep DATADIR TARGET | check IOS.png : reversed px along the target outline, model cached."""
import sys, numpy as np, pickle
from PIL import Image
SP = '/tmp/work/'
C = SP + 'exp/inv_cache.pkl'
if sys.argv[1] == 'prep':
    from pbart import load
    from art import flatten, rasterize
    from pbrender import render
    from score import DS, DOX, DEV
    sh = load(sys.argv[2]); t = int(sys.argv[3]); s = sh[t]
    x0, y0, c = rasterize(flatten(s.subs, DS), DS, DOX, 0, DEV[0], DEV[1], 16); h, w = c.shape
    m = (np.clip(render(sh, DS, DOX - x0, -y0, w, h), 0, 1) * 255 + .5).astype(np.int16)
    ab = np.zeros((h, w))
    for u in sh[t + 1:]:
        r = rasterize(flatten(u.subs, DS), DS, DOX - x0, -y0, w, h, 16)
        if r is None: continue
        a0, b0, cc = r; ab[b0:b0 + cc.shape[0], a0:a0 + cc.shape[1]] = np.maximum(ab[b0:b0 + cc.shape[0], a0:a0 + cc.shape[1]], cc)
    pickle.dump((x0, y0, m, (c > 0.1) & (c < 0.9) & (ab < 0.02)), open(C, 'wb'))
else:
    x0, y0, m, edge = pickle.load(open(C, 'rb')); h, w = edge.shape
    i = np.asarray(Image.open(sys.argv[2]).convert('RGB')).astype(np.int16)[y0:y0 + h, x0:x0 + w]
    print((edge & (np.abs(i - m).max(-1) > 25)).sum())
