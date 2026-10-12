"""Joint least-squares refit of every shape's fill (flat or 2-stop linear gradient) to the reference,
through an exact model of the iOS render: AA coverage, source-over stacking, soft pass."""
import sys, os, time, numpy as np
from scipy import ndimage as ndi, sparse
from scipy.sparse.linalg import spsolve
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000
from art import *
from pathio import path_str

SP = '/tmp/work/'
SOFT, FEATHER = 2.5, 1.0

def coverage(shapes, S=16):
    return [rasterize(flatten(sh.subs, 1.0), 1.0, 0, 0, W, H, S) for sh in shapes]

def visible(covs):
    T = np.ones((H, W)); vis = [None] * len(covs)
    for i in range(len(covs) - 1, -1, -1):
        r = covs[i]
        if r is None: continue
        x0, y0, c = r; h, w = c.shape
        vis[i] = (x0, y0, c * T[y0:y0 + h, x0:x0 + w])
        T[y0:y0 + h, x0:x0 + w] *= (1 - c)
    return vis

def soft_mask(datadir):
    subs = []
    for line in open(os.path.join(datadir, 'softZoneData.txt')).read().split('\n'):
        if line.strip(): subs += parse_path(line.strip())
    r = rasterize(flatten(subs, 1.0), 1.0, 0, 0, W, H, 16)
    m = np.zeros((H, W)); x0, y0, c = r; m[y0:y0 + c.shape[0], x0:x0 + c.shape[1]] = c
    m = ndi.gaussian_filter(m, FEATHER, mode='constant')
    aB = ndi.gaussian_filter(np.ones((H, W)), SOFT, mode='constant')
    return m, aB

def tparam(sh, xs, ys):
    d = sh.p1 - sh.p0; dd = d @ d
    return np.clip(((xs - sh.p0[0]) * d[0] + (ys - sh.p0[1]) * d[1]) / dd, 0, 1)

def refit_axes(shapes, vis, ref, min_de=1.0):
    """Choose flat vs gradient and the gradient axis per shape from the reference colours in its visible area."""
    lab_ref = None
    for sh, v in zip(shapes, vis):
        if v is None: continue
        x0, y0, w = v
        sel = w > 0.5
        if sel.sum() < 12: continue
        ys, xs = np.nonzero(sel); ww = w[sel]
        X = np.stack([xs + x0 + 0.5, ys + y0 + 0.5], 1)
        C = ref[ys + y0, xs + x0]
        mu = (X * ww[:, None]).sum(0) / ww.sum()
        D = X - mu
        A = np.concatenate([np.ones((len(D), 1)), D], 1) * np.sqrt(ww)[:, None]
        coef, *_ = np.linalg.lstsq(A, C * np.sqrt(ww)[:, None], rcond=None)
        B = coef[1:].T            # 3x2 colour change per unit
        u, s, vt = np.linalg.svd(B)
        v_dir = vt[0]
        proj = D @ v_dir
        lo, hi = np.percentile(proj, 2), np.percentile(proj, 98)
        if hi - lo < 2: continue
        ca = coef[0] + B @ (v_dir * lo); cb = coef[0] + B @ (v_dir * hi)
        de = deltaE_ciede2000(rgb2lab(np.clip(ca, 0, 1)[None, None]), rgb2lab(np.clip(cb, 0, 1)[None, None]))[0, 0]
        if de < min_de:
            sh.grad = False; sh.p0 = sh.p1 = None
        else:
            sh.grad = True; sh.p0 = mu + v_dir * lo; sh.p1 = mu + v_dir * hi
            sh.c0, sh.c1 = np.clip(ca, 0, 1), np.clip(cb, 0, 1)

def build(shapes, vis, m, aB):
    K = 1 - m * aB
    rows, cols, vals, owner = [], [], [], []
    pad = int(np.ceil(4 * SOFT)) + 1
    nb = 0
    for i, (sh, v) in enumerate(zip(shapes, vis)):
        if v is None or v[2].sum() < 1e-3:
            continue
        x0, y0, w = v; h, ww = w.shape
        if sh.grad:
            ys, xs = np.mgrid[y0:y0 + h, x0:x0 + ww]
            t = tparam(sh, xs + 0.5, ys + 0.5)
            bases = [w * (1 - t), w * t]
        else:
            bases = [w]
        X0, Y0 = max(x0 - pad, 0), max(y0 - pad, 0); X1, Y1 = min(x0 + ww + pad, W), min(y0 + h + pad, H)
        for k, b in enumerate(bases):
            big = np.zeros((Y1 - Y0, X1 - X0)); big[y0 - Y0:y0 - Y0 + h, x0 - X0:x0 - X0 + ww] = b
            col = K[Y0:Y1, X0:X1] * big + m[Y0:Y1, X0:X1] * ndi.gaussian_filter(big, SOFT, mode='constant', truncate=4)
            yy, xx = np.nonzero(col > 1e-4)
            rows.append((yy + Y0) * W + xx + X0); cols.append(np.full(len(yy), nb)); vals.append(col[yy, xx])
            owner.append((i, k)); nb += 1
    A = sparse.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(W * H, nb))
    return A, owner

def solve(A, owner, shapes, ref, lam=0.2):
    r = ref.reshape(-1, 3)
    prior = np.array([shapes[i].c0 if k == 0 else shapes[i].c1 for i, k in owner])
    AtA = (A.T @ A).tocsc(); Atr = A.T @ r
    R = sparse.identity(A.shape[1], format='csc') * lam
    X = np.stack([spsolve(AtA + R, Atr[:, c] + lam * prior[:, c]) for c in range(3)], 1)
    return np.clip(X, 0, 1)

def transfer_hidden(shapes, vis, old):
    """Shapes with no visible area: map old colours through a kNN old->new transfer learned per layer."""
    for L in LAYERS:
        idx = [i for i, s in enumerate(shapes) if s.layer == L]
        known = [i for i in idx if vis[i] is not None and vis[i][2].sum() > 20]
        unk = [i for i in idx if vis[i] is None or vis[i][2].sum() <= 1e-3]
        if not known or not unk: continue
        src = rgb2lab(np.array([old[i][0] for i in known])[None])[0]
        dst = np.array([shapes[i].c0 for i in known])
        for i in unk:
            for which in (0, 1):
                q = rgb2lab(np.array(old[i][which])[None, None])[0, 0]
                d = np.linalg.norm(src - q, axis=1); nn = np.argsort(d)[:8]
                wgt = 1 / (d[nn] + 1); c = (dst[nn] * wgt[:, None]).sum(0) / wgt.sum()
                if which == 0: shapes[i].c0 = c
                else: shapes[i].c1 = c
            if not shapes[i].grad: shapes[i].c1 = shapes[i].c0

def predict(A, owner, X):
    return np.clip((A @ X).reshape(H, W, 3), 0, 1)

def write(shapes, src, dst):
    os.makedirs(dst, exist_ok=True)
    for L in LAYERS:
        lines = []
        for sh in [s for s in shapes if s.layer == L]:
            if sh.grad:
                lines.append('%s %s %.1f %.1f %.1f %.1f %s' % (rgb2hex(sh.c0), rgb2hex(sh.c1), sh.p0[0], sh.p0[1], sh.p1[0], sh.p1[1], sh.pathstr))
            else:
                lines.append('%s %s' % (rgb2hex(sh.c0), sh.pathstr))
        open(os.path.join(dst, L + '.txt'), 'w').write('\n'.join(lines) + '\n')
    os.system(f'cp {src}/softZoneData.txt {dst}/')

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    t = time.time()
    ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
    shapes = load(src); old = [(s.c0.copy(), s.c1.copy()) for s in shapes]
    covs = coverage(shapes); vis = visible(covs); print('raster+visible %.1fs' % (time.time() - t))
    m, aB = soft_mask(src)
    refit_axes(shapes, vis, ref); print('axes: %d gradients / %d shapes' % (sum(s.grad for s in shapes), len(shapes)))
    A, owner = build(shapes, vis, m, aB); print('A', A.shape, 'nnz', A.nnz, '%.1fs' % (time.time() - t))
    X = solve(A, owner, shapes, ref); print('solved %.1fs' % (time.time() - t))
    for (i, k), c in zip(owner, X):
        if k == 0: shapes[i].c0 = c
        else: shapes[i].c1 = c
    for (i, k) in owner:
        if not shapes[i].grad: shapes[i].c1 = shapes[i].c0
    transfer_hidden(shapes, vis, old)
    P = predict(A, owner, X)
    de = deltaE_ciede2000(rgb2lab(P), rgb2lab(ref))
    print('predicted (python model) mean dE00 %.2f p95 %.2f' % (de.mean(), np.percentile(de, 95)))
    np.save(SP + 'out/pred.npy', P.astype(np.float32))
    write(shapes, src, dst)
