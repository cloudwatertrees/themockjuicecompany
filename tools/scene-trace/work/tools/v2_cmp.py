"""v2: compare data sets on one crop: reference bicubic | each data dir rendered by the Python model at SCALE
(matches the iOS CPU renderer), magnified MAG x nearest-neighbour.
usage: v2_cmp.py x0,y0,x1,y1 SCALE MAG OUT.png DATADIR [...]   (run from tools/)"""
import sys, numpy as np
from PIL import Image
from pbart import load
from pbrender import render
from score import SP

x0, y0, x1, y1 = map(int, sys.argv[1].split(',')); s = float(sys.argv[2]); mag = int(sys.argv[3]); out = sys.argv[4]
w, h = round((x1 - x0) * s), round((y1 - y0) * s)
tiles = [Image.open(SP + 'ref/ref.png').convert('RGB').crop((x0, y0, x1, y1)).resize((w, h), Image.BICUBIC)]
for d in sys.argv[5:]:
    img = render(load(d), s, -x0 * s, -y0 * s, w, h)
    tiles.append(Image.fromarray((np.clip(img, 0, 1) * 255).round().astype(np.uint8)))
o = Image.new('RGB', (len(tiles) * (w * mag + 8), h * mag), 'white')
for k, t in enumerate(tiles): o.paste(t.resize((w * mag, h * mag), Image.NEAREST), (k * (w * mag + 8), 0))
o.save(out); print('wrote', out, o.size)
