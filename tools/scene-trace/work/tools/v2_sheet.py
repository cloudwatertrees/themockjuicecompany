"""v2: inspection sheet. Crops of a full-canvas render (reference framing, the reference's size in pt at SCALE) beside the reference
bicubic-upscaled to the same scale, magnified MAG x with nearest-neighbour so device pixels stay visible.
usage: v2_sheet.py RENDER.png SCALE MAG OUT.png x0,y0,x1,y1 [...]   (boxes in design units; run from tools/)"""
import sys, numpy as np
from PIL import Image
from score import SP

ren = Image.open(sys.argv[1]).convert('RGB'); s = float(sys.argv[2]); mag = int(sys.argv[3]); out = sys.argv[4]
ref = Image.open(SP + 'ref/ref.png').convert('RGB')
rows = []
for b in sys.argv[5:]:
    x0, y0, x1, y1 = map(int, b.split(','))
    w, h = round((x1 - x0) * s), round((y1 - y0) * s)
    a = ref.crop((x0, y0, x1, y1)).resize((w, h), Image.BICUBIC)
    r = ren.crop((round(x0 * s), round(y0 * s), round(x0 * s) + w, round(y0 * s) + h))
    t = Image.new('RGB', (2 * w * mag + 8, h * mag), 'white')
    t.paste(a.resize((w * mag, h * mag), Image.NEAREST), (0, 0)); t.paste(r.resize((w * mag, h * mag), Image.NEAREST), (w * mag + 8, 0))
    rows.append(t)
o = Image.new('RGB', (max(t.width for t in rows), sum(t.height + 8 for t in rows)), 'white')
y = 0
for t in rows: o.paste(t, (0, y)); y += t.height + 8
o.save(out); print('wrote', out, o.size)
