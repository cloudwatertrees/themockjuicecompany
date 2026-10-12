import numpy as np, time
from art import *

def composite(shapes, scale=1.0, ox=0.0, oy=0.0, Wp=W, Hp=H, S=16, keep_cov=False):
    img = np.zeros((Hp, Wp, 3)); alpha = np.zeros((Hp, Wp))
    covs = [] if keep_cov else None
    for sh in shapes:
        r = rasterize(flatten(sh.subs, scale), scale, ox, oy, Wp, Hp, S)
        if keep_cov: covs.append(r)
        if r is None: continue
        x0, y0, cov = r
        h, w = cov.shape
        ys, xs = np.mgrid[y0:y0 + h, x0:x0 + w]
        col = shading(sh, (xs + 0.5 - ox) / scale, (ys + 0.5 - oy) / scale)
        a = cov[..., None]
        img[y0:y0 + h, x0:x0 + w] = img[y0:y0 + h, x0:x0 + w] * (1 - a) + col * a
        alpha[y0:y0 + h, x0:x0 + w] = alpha[y0:y0 + h, x0:x0 + w] * (1 - cov) + cov
    return img, alpha, covs
