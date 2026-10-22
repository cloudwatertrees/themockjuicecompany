"""Tile images into a sheet at most MAXW px wide: python tile.py OUT MAXW img1 img2 ..."""
import sys
import numpy as np
from PIL import Image
out, maxw = sys.argv[1], int(sys.argv[2])
ims = [Image.open(p).convert('RGB') for p in sys.argv[3:]]
rows, row, w = [], [], 0
for im in ims:
    if row and w + im.width > maxw:
        rows.append(row); row, w = [], 0
    row.append(im); w += im.width + 6
rows.append(row)
H = sum(max(i.height for i in r) + 6 for r in rows); Wd = max(sum(i.width + 6 for i in r) for r in rows)
sheet = Image.new('RGB', (Wd, H), (255, 255, 255)); y = 0
for r in rows:
    x = 0
    for i in r:
        sheet.paste(i, (x, y)); x += i.width + 6
    y += max(i.height for i in r) + 6
sheet.save(out); print(out, sheet.size)
