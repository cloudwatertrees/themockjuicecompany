"""Measure cream-path and brown-verge extents per row near the A/B join, and row-difference baselines."""
import numpy as np
from PIL import Image
A = np.asarray(Image.open('A.png').convert('RGB')).astype(np.float32)
B = np.asarray(Image.open('B_orig.png').convert('RGB')).astype(np.float32)

def cream(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    return (r > 215) & (g > 195) & (b > 160) & (r - b < 70) & (r >= g)

def brown(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    return (r > 110) & (r < 215) & (r - g > 25) & (g - b > 5) & (r - b > 45)

def runs(m):
    """Largest run of True in a 1-D mask after closing small gaps."""
    from scipy.ndimage import binary_closing
    m = binary_closing(m, np.ones(9))
    idx = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0]))
    rs = list(zip(idx[::2], idx[1::2]))
    return max(rs, key=lambda r: r[1] - r[0]) if rs else (0, 0)

for name, img, rows in [('A', A, [1477, 1557, 1617, 1657, 1677]), ('B', B, [0, 10, 20, 40, 60, 80, 120, 160, 200])]:
    c, br = cream(img), brown(img)
    for y in rows:
        x0, x1 = runs(c[y])
        bm = br[y].copy(); bm[:x1] = False
        b0, b1 = runs(bm[:])
        bl = br[y].copy(); bl[x0:] = False
        l0, l1 = runs(bl)
        print(f'{name} row {y}: path {x0}-{x1} ({x1-x0}), right verge {b0}-{b1}, left verge {l0}-{l1}')

def L(img): return img @ np.array([0.299, 0.587, 0.114], np.float32)
la, lb = L(A)[:, 81:857], L(B)[:, 81:857]
d = np.abs(np.diff(la, axis=0)).mean(1)
print('A neighbour-row mean |dL| bottom200: mean %.2f p95 %.2f max %.2f; whole A mean %.2f p95 %.2f' % (
    d[-200:].mean(), np.percentile(d[-200:], 95), d[-200:].max(), d.mean(), np.percentile(d, 95)))
print('raw seam |A1677 - B0| = %.2f' % np.abs(la[-1] - lb[0]).mean())
