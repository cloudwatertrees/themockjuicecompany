"""Joint least-squares refit of every shape's fill through the exact extended-grid iOS render model."""
import sys, os, time, numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000
from model import *
from fit import write, transfer_hidden

SP = '/tmp/work/'

def tparam(sh, xs, ys):
    d = sh.p1 - sh.p0; dd = d @ d
    return np.clip(((xs - sh.p0[0]) * d[0] + (ys - sh.p0[1]) * d[1]) / dd, 0, 1)

def refit_axes(shapes, vis, refx, min_de=1.0, keep_axes=False):
    """Per shape: flat vs gradient + axis from the reference over its on-canvas visible area.
    Also sets prior colours (c0, c1). refx: reference edge-padded onto the extended grid."""
    for sh, v in zip(shapes, vis):
        if v is None: continue
        x0, y0, w = v
        on = np.zeros_like(w, bool)
        ys_, xs_ = np.mgrid[y0:y0 + w.shape[0], x0:x0 + w.shape[1]]
        on = (xs_ >= M) & (xs_ < M + W) & (ys_ >= M) & (ys_ < M + H)
        sel = (w > 0.5) & on
        if sel.sum() < 12:
            sel2 = w > 1e-3
            if sel2.any():
                ww = w[sel2]; c = (refx[ys_[sel2], xs_[sel2]] * ww[:, None]).sum(0) / ww.sum()
                if not sh.grad or not keep_axes:
                    sh.grad = False; sh.c0 = sh.c1 = c
            continue
        ys, xs = ys_[sel], xs_[sel]; ww = w[sel]
        X = np.stack([xs + 0.5 - M, ys + 0.5 - M], 1)
        C = refx[ys, xs]
        mu = (X * ww[:, None]).sum(0) / ww.sum()
        D = X - mu
        A = np.concatenate([np.ones((len(D), 1)), D], 1) * np.sqrt(ww)[:, None]
        coef, *_ = np.linalg.lstsq(A, C * np.sqrt(ww)[:, None], rcond=None)
        B = coef[1:].T
        if keep_axes and sh.grad:
            sh.c0 = np.clip(coef[0] + B @ (sh.p0 - mu), 0, 1); sh.c1 = np.clip(coef[0] + B @ (sh.p1 - mu), 0, 1)
            continue
        u, s, vt = np.linalg.svd(B)
        v_dir = vt[0]
        proj = D @ v_dir
        lo, hi = np.percentile(proj, 2), np.percentile(proj, 98)
        ca = coef[0] + B @ (v_dir * lo); cb = coef[0] + B @ (v_dir * hi)
        de = deltaE_ciede2000(rgb2lab(np.clip(ca, 0, 1)[None, None]), rgb2lab(np.clip(cb, 0, 1)[None, None]))[0, 0]
        if hi - lo < 2 or de < min_de:
            sh.grad = False; sh.p0 = sh.p1 = None; sh.c0 = sh.c1 = np.clip(coef[0], 0, 1)
        else:
            sh.grad = True; sh.p0 = mu + v_dir * lo; sh.p1 = mu + v_dir * hi
            sh.c0, sh.c1 = np.clip(ca, 0, 1), np.clip(cb, 0, 1)

def build(shapes, vis, alpha, covs, datadir):
    box = union_box(covs); m = soft_mask(datadir); Ba = blur_box(alpha, box, SOFT)
    K = 1 - m * Ba
    rows, cols, vals, owner = [], [], [], []
    nb = 0
    def add(X0, Y0, img, scale):
        # crop to canvas, weight, emit
        h, w = img.shape
        cx0, cy0 = max(X0, M), max(Y0, M); cx1, cy1 = min(X0 + w, M + W), min(Y0 + h, M + H)
        if cx1 <= cx0 or cy1 <= cy0: return
        sub = img[cy0 - Y0:cy1 - Y0, cx0 - X0:cx1 - X0] * scale[cy0:cy1, cx0:cx1]
        yy, xx = np.nonzero(sub > 1e-4)
        rows.append((yy + cy0 - M) * W + xx + cx0 - M); cols.append(np.full(len(yy), nb)); vals.append(sub[yy, xx])
    for i, (sh, v) in enumerate(zip(shapes, vis)):
        if v is None or v[2].sum() < 1e-3: continue
        x0, y0, w = v; h, ww = w.shape
        if sh.grad:
            ys, xs = np.mgrid[y0:y0 + h, x0:x0 + ww]
            t = tparam(sh, xs + 0.5 - M, ys + 0.5 - M)
            bases = [w * (1 - t), w * t]
        else:
            bases = [w]
        for k, b in enumerate(bases):
            add(x0, y0, b, K)
            X0, Y0, g = local_blur(b, x0, y0, box)
            add(X0, Y0, g, m)
            owner.append((i, k)); nb += 1
    A = sparse.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(W * H, nb))
    A.sum_duplicates()
    return A.tocsc(), owner

def solve(A, owner, shapes, ref, lam=0.2, lam_rel=0.0):
    r = ref.reshape(-1, 3)
    prior = np.array([shapes[i].c0 if k == 0 else shapes[i].c1 for i, k in owner])
    AtA = (A.T @ A).tocsc(); Atr = A.T @ r
    R = sparse.diags(lam + lam_rel * np.asarray(AtA.diagonal()).ravel(), format='csc')
    lam = R.diagonal()[:, None]
    X = np.stack([spsolve(AtA + R, Atr[:, c] + lam[:, 0] * prior[:, c]) for c in range(3)], 1)
    return np.clip(X, 0, 1)

def run(src, dst, min_de=1.0, keep_axes=False, lam=0.2, lam_rel=0.0):
    t = time.time()
    ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
    refx = np.pad(ref, ((M, M), (M, M), (0, 0)), mode='edge')
    shapes = load(src); old = [(s.c0.copy(), s.c1.copy()) for s in shapes]
    covs = coverage(shapes); vis, alpha = visible(covs)
    refit_axes(shapes, vis, refx, min_de, keep_axes)
    A, owner = build(shapes, vis, alpha, covs, src)
    X = solve(A, owner, shapes, ref, lam, lam_rel)
    for (i, k), c in zip(owner, X):
        if k == 0: shapes[i].c0 = c
        else: shapes[i].c1 = c
    for (i, k) in owner:
        if not shapes[i].grad: shapes[i].c1 = shapes[i].c0
    transfer_hidden(shapes, [v if v is None or v[2].sum() > 1e-3 else None for v in vis], old)
    P = np.clip((A @ X).reshape(H, W, 3), 0, 1)
    de = deltaE_ciede2000(rgb2lab(P), rgb2lab(ref))
    print('%d shapes, %d gradients, %d unknowns/channel, nnz %d; predicted mean dE00 %.3f p95 %.2f (%.0fs)' % (
        len(shapes), sum(s.grad for s in shapes), A.shape[1], A.nnz, de.mean(), np.percentile(de, 95), time.time() - t))
    write(shapes, src, dst)
    return shapes

if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2], lam_rel=float(sys.argv[3]) if len(sys.argv) > 3 else 0.0)
