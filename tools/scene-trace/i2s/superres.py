"""Sub-pixel boundary placement: reassign sub-pixels near label boundaries to the neighbouring region whose
affine colour model best matches the bicubic-upsampled reference."""
import numpy as np
import cv2
from regions import region_stats, SCALE


def affine_models(lab, img):
    """Per-region colour planes: n x 3 (constant, x slope, y slope) x 3 (RGB)."""
    st = region_stats(lab, np.dstack([img, img[..., :1]]))
    n = len(st['n'])
    TH = np.zeros((n, 3, 3))
    for i in range(n):
        N = st['n'][i]
        if N < 8:
            TH[i, 0] = st['sc'][i][:3] / max(N, 1)
            continue
        A = np.array([[N, st['sx'][i], st['sy'][i]], [st['sx'][i], st['sxx'][i] + 1e-3 * N, st['sxy'][i]],
                      [st['sy'][i], st['sxy'][i], st['syy'][i] + 1e-3 * N]])
        B = np.stack([st['sc'][i][:3], st['scx'][i][:3], st['scy'][i][:3]])
        TH[i] = np.linalg.solve(A, B)
    return TH


def superres(lab, ref, TH, U=4, chunk=40000):
    """Label map at U times the resolution with boundaries re-placed against the reference."""
    H, W = lab.shape
    OX, OY = W / 2, H / 2
    refU = cv2.resize(ref.astype(np.float32), (W * U, H * U), interpolation=cv2.INTER_CUBIC)
    pad = np.pad(lab, 1, mode='edge')
    nb = np.stack([pad[dy:dy + H, dx:dx + W] for dy in range(3) for dx in range(3)], -1)
    bnd = (nb != lab[..., None]).any(-1)
    ys, xs = np.nonzero(bnd)
    LU = np.repeat(np.repeat(lab, U, 0), U, 1)
    off = (np.arange(U) + 0.5) / U
    oy, ox = np.meshgrid(off, off, indexing='ij')
    oy = oy.ravel()
    ox = ox.ravel()  # U*U
    for s in range(0, len(ys), chunk):
        y = ys[s:s + chunk]
        x = xs[s:s + chunk]
        cand = nb[y, x]  # M x 9
        px = x[:, None] + ox[None]
        py = y[:, None] + oy[None]  # M x UU
        xn = (px - OX) / SCALE
        yn = (py - OY) / SCALE
        T = TH[cand]  # M x 9 x 3 x 3
        col = T[:, None, :, 0, :] + T[:, None, :, 1, :] * xn[:, :, None, None] + T[:, None, :, 2, :] * yn[:, :, None, None]
        iy = (y[:, None] * U + (np.arange(U)[:, None] * np.ones(U, int)[None]).ravel()[None])
        ix = (x[:, None] * U + (np.ones(U, int)[:, None] * np.arange(U)[None]).ravel()[None])
        tgt = refU[iy, ix]  # M x UU x 3
        d = ((col - tgt[:, :, None, :]) ** 2).sum(-1)  # M x UU x 9
        k = d.argmin(-1)
        LU[iy, ix] = np.take_along_axis(cand[:, None, :].repeat(U * U, 1), k[..., None], -1)[..., 0]
    return LU
