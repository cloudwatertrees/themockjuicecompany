"""Exact model of the iOS render on an extended grid (off-canvas content matters for the soft pass).
Measured iOS behaviour: blur layer buffer = union(canvas, content bounds), clamp-to-edge outside it;
SwiftUI blur radius == Gaussian sigma (2.467 px measured at 1x for radius 2.5)."""
import os, numpy as np
from scipy import ndimage as ndi
from art import *

M = 16                      # extended-grid margin (px at 1x)
WX, HX = W + 2 * M, H + 2 * M
SOFT, FEATHER = 2.467, 0.987

def coverage(shapes, S=16):
    return [rasterize(flatten(sh.subs, 1.0), 1.0, M, M, WX, HX, S) for sh in shapes]

def visible(covs):
    T = np.ones((HX, WX)); vis = [None] * len(covs)
    for i in range(len(covs) - 1, -1, -1):
        r = covs[i]
        if r is None: continue
        x0, y0, c = r; h, w = c.shape
        vis[i] = (x0, y0, c * T[y0:y0 + h, x0:x0 + w])
        T[y0:y0 + h, x0:x0 + w] *= (1 - c)
    return vis, 1 - T

def union_box(covs):
    xs0 = [M]; ys0 = [M]; xs1 = [M + W]; ys1 = [M + H]
    for r in covs:
        if r is None: continue
        x0, y0, c = r
        nz = np.nonzero(c > 1e-3)
        if len(nz[0]) == 0: continue
        ys0.append(y0 + nz[0].min()); ys1.append(y0 + nz[0].max() + 1)
        xs0.append(x0 + nz[1].min()); xs1.append(x0 + nz[1].max() + 1)
    return min(xs0), min(ys0), max(xs1), max(ys1)

def blur_box(img, box, s):
    """Gaussian over the buffer box with clamp-to-edge; zero outside the box beforehand."""
    X0, Y0, X1, Y1 = box
    out = np.zeros_like(img)
    out[Y0:Y1, X0:X1] = ndi.gaussian_filter(img[Y0:Y1, X0:X1], s, mode='nearest', truncate=4)
    return out

def soft_mask(datadir):
    subs = []
    for line in open(os.path.join(datadir, 'softZoneData.txt')).read().split('\n'):
        if line.strip(): subs += parse_path(line.strip())
    r = rasterize(flatten(subs, 1.0), 1.0, M, M, WX, HX, 16)
    mk = np.zeros((HX, WX)); x0, y0, c = r; mk[y0:y0 + c.shape[0], x0:x0 + c.shape[1]] = c
    box = union_box([r])
    return blur_box(mk, box, FEATHER)

def local_blur(b, x0, y0, box, s=SOFT):
    """Blur a local basis image placed at (x0, y0) in the extended grid, with the buffer's clamp-to-edge.
    Returns (X0, Y0, blurred) over a padded window."""
    pad = int(np.ceil(4 * s)) + 1
    BX0, BY0, BX1, BY1 = box
    h, w = b.shape
    X0, Y0 = max(x0 - pad, BX0), max(y0 - pad, BY0)
    X1, Y1 = min(x0 + w + pad, BX1), min(y0 + h + pad, BY1)
    big = np.zeros((Y1 - Y0, X1 - X0))
    sy0, sx0 = max(y0, Y0), max(x0, X0); sy1, sx1 = min(y0 + h, Y1), min(x0 + w, X1)
    big[sy0 - Y0:sy1 - Y0, sx0 - X0:sx1 - X0] = b[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0]
    el, et = (pad if X0 == BX0 else 0), (pad if Y0 == BY0 else 0)
    er, eb = (pad if X1 == BX1 else 0), (pad if Y1 == BY1 else 0)
    if el or et or er or eb:
        big = np.pad(big, ((et, eb), (el, er)), mode='edge')
    g = ndi.gaussian_filter(big, s, mode='constant', truncate=4)
    return X0, Y0, g[et:et + Y1 - Y0, el:el + X1 - X0]

def render(shapes, datadir, soft=True):
    """Full predicted render (canvas crop) for the given shapes (colours as stored)."""
    covs = coverage(shapes); vis, alpha = visible(covs)
    img = np.zeros((HX, WX, 3))
    for sh, v in zip(shapes, vis):
        if v is None: continue
        x0, y0, w = v; h, ww = w.shape
        ys, xs = np.mgrid[y0:y0 + h, x0:x0 + ww]
        img[y0:y0 + h, x0:x0 + ww] += shading(sh, xs + 0.5 - M, ys + 0.5 - M) * w[..., None]
    if not soft:
        return img[M:M + H, M:M + W]
    box = union_box(covs); m = soft_mask(datadir)
    B = np.stack([blur_box(img[..., c], box, SOFT) for c in range(3)], -1); Ba = blur_box(alpha, box, SOFT)
    fin = img * (1 - (m * Ba))[..., None] + B * m[..., None]
    return fin[M:M + H, M:M + W]
