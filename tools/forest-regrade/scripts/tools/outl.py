"""outl.py DEVX DEVY R LAYERS OUT : model render (6x) with outlines of shapes in LAYERS (index labels)."""
import sys, numpy as np
from PIL import Image, ImageDraw
from pbart import load
from pbrender import render
from art import flatten
from score import DS, DOX
SP = '/tmp/work/'
sx, sy, R = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]); layers = sys.argv[4].split(','); out = sys.argv[5]
sh = load(SP + 'data/pb22')
X0, Y0, X1, Y1 = (sx - R - DOX) / DS, (sy - R) / DS, (sx + R - DOX) / DS, (sy + R) / DS
idx = [k for k, s in enumerate(sh) if s.box[0] <= X1 and s.box[2] >= X0 and s.box[1] <= Y1 and s.box[3] >= Y0]
m = render([sh[k] for k in idx], DS, DOX - (sx - R), -(sy - R), 2 * R, 2 * R)
z = 12; M = Image.fromarray((np.clip(m, 0, 1) * 255 + .5).astype(np.uint8)).resize((2 * R * z, 2 * R * z), Image.NEAREST)
d = ImageDraw.Draw(M); rng = np.random.default_rng(1)
for k in idx:
    s = sh[k]
    if s.layer not in layers: continue
    col = tuple(int(v) for v in rng.integers(0, 255, 3))
    for poly in flatten(s.subs, DS):
        P = [((px * DS + DOX - (sx - R)) * z, (py * DS - (sy - R)) * z) for px, py in np.asarray(poly)]
        d.line(P + [P[0]], fill=col, width=1)
        d.text(P[0], str(k), fill=col)
M.save(out)
