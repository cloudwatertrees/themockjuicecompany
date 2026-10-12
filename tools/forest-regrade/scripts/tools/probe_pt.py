"""probe_pt.py DEVX DEVY [R] : shapes covering a device-pixel point (topmost last) + zoom render|ref."""
import sys, numpy as np
from PIL import Image
from pbart import load
from art import flatten, rasterize
from score import DS, DOX, rgb, to_device
SP = '/tmp/work/'
sx, sy = int(sys.argv[1]), int(sys.argv[2]); R = int(sys.argv[3]) if len(sys.argv) > 3 else 20
X, Y = (sx + .5 - DOX) / DS, (sy + .5) / DS
print('design %.1f %.1f' % (X, Y))
sh = load(SP + 'data/' + (sys.argv[4] if len(sys.argv) > 4 else 'pb22'))
for k, s in enumerate(sh):
    if not (s.box[0] <= X + 1 and s.box[2] >= X - 1 and s.box[1] <= Y + 1 and s.box[3] >= Y - 1): continue
    r = rasterize(flatten(s.subs, DS), DS, DOX - (sx - 2), -(sy - 2), 5, 5, 16)
    if r is None: continue
    x0, y0, c = r; full = np.zeros((5, 5)); full[y0:y0 + c.shape[0], x0:x0 + c.shape[1]] = c
    if full[2, 2] < 0.02 and full.max() < 0.3: continue
    segs = sum(len(u) - 1 for u in s.subs)
    area = 0
    col = (s.colour_at(np.array([X]), np.array([Y]))[0] * 255).round().astype(int)
    print('#%d %-10s cov@pt %.2f  nx %d ny %d segs %d box %s colour %s' % (k, s.layer, full[2, 2], s.nx, s.ny, segs, ','.join('%.1f' % v for v in s.box), col.tolist()))
ios = Image.open(SP + 'out/repoC/dev3x.png').convert('RGB')
refd = Image.fromarray((to_device(rgb(SP + 'ref/ref.png')) * 255 + .5).astype(np.uint8))
z = 6; b = (sx - R, sy - R, sx + R, sy + R)
c = Image.new('RGB', (2 * 2 * R * z + 8, 2 * R * z), 'white')
c.paste(ios.crop(b).resize((2 * R * z, 2 * R * z), Image.NEAREST), (0, 0)); c.paste(refd.crop(b).resize((2 * R * z, 2 * R * z), Image.NEAREST), (2 * R * z + 8, 0))
c.save(SP + 'out/zz_pt.png')
