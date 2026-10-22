"""Blind test set: 12 crops from x 81..856, 6 across the A/B join and 6 interior controls from A, shuffled and neutrally
named. The key goes to a separate file the reviewer never sees.

usage: blind.py B_SEAM.png OUTDIR [SEED]
OUTDIR/crops/img_01.png .. img_12.png, OUTDIR/key.txt. Join crops place the join at a random height inside the crop
(25-75%); controls are cut from A at random rows with the same sizes and zooms, so position gives nothing away.
"""
import os
import sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
A = np.asarray(Image.open(os.path.join(os.path.dirname(HERE), 'A.png')).convert('RGB'))
B = np.asarray(Image.open(sys.argv[1]).convert('RGB'))
out = sys.argv[2]
rng = np.random.default_rng(int(sys.argv[3]) if len(sys.argv) > 3 else 7)
H, W = A.shape[:2]
comp = np.vstack([A, B])
os.makedirs(os.path.join(out, 'crops'), exist_ok=True)

# (window width, height, zoom): wide 1x views down to tight 3x views; each size is used once for a join and once for a control
SIZES = [(560, 320, 1), (420, 260, 1), (300, 200, 2), (260, 180, 2), (200, 150, 3), (160, 120, 3)]
items = []
for w, h, z in SIZES:
    # join crop: random x window inside 81..856, join at 25-75% of the height
    x0 = int(rng.integers(81, 857 - w + 1))
    f = rng.uniform(0.25, 0.75)
    y0 = H - int(round(h * f))
    items.append(('join', comp[y0:y0 + h, x0:x0 + w], z, (x0, y0 - H, w, h)))
    # control from A's interior, away from its top and bottom 120 rows
    x1 = int(rng.integers(81, 857 - w + 1))
    y1 = int(rng.integers(120, H - 120 - h))
    items.append(('control', A[y1:y1 + h, x1:x1 + w], z, (x1, y1, w, h)))
order = rng.permutation(len(items))
key = []
for n, i in enumerate(order, 1):
    kind, img, z, box = items[i]
    im = Image.fromarray(img)
    if z > 1:
        im = im.resize((im.width * z, im.height * z), Image.LANCZOS)
    name = f'img_{n:02d}.png'
    im.save(os.path.join(out, 'crops', name))
    where = f'join at y={-box[1]} of {box[3]} (x {box[0]}..{box[0] + box[2]})' if kind == 'join' else f'A x {box[0]}..{box[0] + box[2]}, y {box[1]}..{box[1] + box[3]}'
    key.append(f'{name}\t{kind}\tzoom {z}x\t{where}')
open(os.path.join(out, 'key.txt'), 'w').write('\n'.join(key) + '\n')
print('\n'.join(key))
