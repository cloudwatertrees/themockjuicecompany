"""complayers.py PREFIX OUT.png : source-over composite of per-layer transparent renders (premultiplied 8-bit PNGs)."""
import sys, numpy as np
from PIL import Image
from art import LAYERS
pre, out = sys.argv[1], sys.argv[2]
acc = None
for L in LAYERS:
    im = np.asarray(Image.open(pre + '_' + L + '.png').convert('RGBA')).astype(np.float64) / 255
    a = im[..., 3:4]; col = im[..., :3] * a          # PNG is straight alpha -> premultiply
    acc = col if acc is None else col + acc * (1 - a)
Image.fromarray((np.clip(acc, 0, 1) * 255 + .5).astype(np.uint8)).save(out)
