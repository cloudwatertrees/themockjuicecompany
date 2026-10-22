"""Composite two variants that edited disjoint sides of the same base: left image for x < X, right image for x >= X.
usage: compose.py LEFT_DIR RIGHT_DIR X OUT_DIR   (merges edits.npz too: left masks cut to x < X, right to x >= X)"""
import os, sys
import numpy as np
from PIL import Image
L, R, X, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
os.makedirs(out, exist_ok=True)
a = np.asarray(Image.open(os.path.join(L, 'B_seam.png')).convert('RGB')).copy()
b = np.asarray(Image.open(os.path.join(R, 'B_seam.png')).convert('RGB'))
a[:, X:] = b[:, X:]
Image.fromarray(a).save(os.path.join(out, 'B_seam.png'))
masks = {}
for d, side in [(L, 'L'), (R, 'R')]:
    p = os.path.join(d, 'edits.npz')
    if os.path.exists(p):
        for k, m in np.load(p).items():
            m = m.copy()
            if side == 'L': m[:, X:] = 0
            else: m[:, :X] = 0
            if m.max() > 0: masks[f'{side}_{k}'] = m
np.savez(os.path.join(out, 'edits.npz'), **masks)
print('composited', out, 'masks', list(masks))
