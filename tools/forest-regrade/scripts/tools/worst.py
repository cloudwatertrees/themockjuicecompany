"""Rank tiles by low-passed dE00 and build crop sheets: render | reference | heat (4x nearest)."""
import sys, numpy as np
from PIL import Image
from score import heat, SP
tag = sys.argv[1]; T = int(sys.argv[2]) if len(sys.argv) > 2 else 48; n = int(sys.argv[3]) if len(sys.argv) > 3 else 8
delp = np.load(SP + f'out/{tag}/delp.npy')
ren = Image.open(SP + f'out/{tag}/ref1x.png').convert('RGB'); ref = Image.open(SP + 'ref/ref.png').convert('RGB')
H, W = delp.shape
scores = []
for y in range(0, H - T + 1, T // 2):
    for x in range(0, W - T + 1, T // 2):
        scores.append((delp[y:y + T, x:x + T].mean(), y, x))
scores.sort(reverse=True)
picked = []
for s, y, x in scores:
    if all(abs(y - py) >= T or abs(x - px) >= T for _, py, px in picked):
        picked.append((s, y, x))
    if len(picked) == n: break
z = 4; rows = []
for s, y, x in picked:
    print('tile y=%d x=%d  lowpass dE00 mean %.2f max %.2f' % (y, x, s, delp[y:y + T, x:x + T].max()))
    box = (x, y, x + T, y + T)
    hm = Image.fromarray((heat(delp[y:y + T, x:x + T], 6) * 255).astype(np.uint8))
    row = Image.new('RGB', (T * z * 3 + 8, T * z), (255, 255, 255))
    for k, im in enumerate([ren.crop(box), ref.crop(box), hm]):
        row.paste(im.resize((T * z, T * z), Image.NEAREST), (k * (T * z + 4), 0))
    rows.append(row)
sheet = Image.new('RGB', (rows[0].width, sum(r.height + 4 for r in rows)), (255, 255, 255))
yy = 0
for r in rows: sheet.paste(r, (0, yy)); yy += r.height + 4
sheet.save(SP + f'out/{tag}/worst.png')
