"""Fit fills of a subset of shapes (bilinear meshes, flat for tiny ones) through the exact render model, all other
shapes fixed. usage: pb_fitsub.py SRC_DATADIR DONOR_DATADIR LAYER CELL DST_DATADIR
Donor shapes of LAYER (geometry only) are drawn after SRC's shapes of LAYER and fitted; the rest keep SRC colours."""
import os, sys, time, numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000
import model
from model import M
from art import W, H, LAYERS
from pbart import PShape, load, write
from pb_fit import grid_for, bil_rows
SP = '/tmp/work/'
src, donor, layer, cell, dst = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5]
lam_s = 0.003; lam_m = float(os.environ.get('PB_LAM_M', '0'))   # mesh second differences; first differences on every edge
t0 = time.time()
base = load(src)
if donor == '-':          # refit the listed shapes in place (mesh dims kept)
    shapes = base; fit = {int(v) for v in layer.split(',')}; new = [shapes[k] for k in sorted(fit)]
else:
    paths = []
    for line in open(donor + '/' + layer + '.txt').read().split('\n'):
        if line.strip(): paths.append(line[line.index('M'):].strip())
    new = [PShape(layer, pathstr=p) for p in paths]
    last = max(k for k, s in enumerate(base) if s.layer == layer)
    shapes = base[:last + 1] + new + base[last + 1:]
    fit = set(range(last + 1, last + 1 + len(new)))
ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
covs = model.coverage(shapes); vis, _ = model.visible(covs)
# fixed part of the prediction
fixed = np.zeros((H, W, 3))
for k, (sh, v) in enumerate(zip(shapes, vis)):
    if k in fit or v is None: continue
    x0, y0, w = v; hh, ww = w.shape
    cy0, cy1 = max(y0, M), min(y0 + hh, M + H); cx0, cx1 = max(x0, M), min(x0 + ww, M + W)
    if cy1 <= cy0 or cx1 <= cx0: continue
    ys, xs = np.mgrid[cy0 - M:cy1 - M, cx0 - M:cx1 - M]
    fixed[cy0 - M:cy1 - M, cx0 - M:cx1 - M] += sh.colour_at(xs + 0.5, ys + 0.5) * w[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0][..., None]
# unknowns for the fitted shapes
order = sorted(fit); off = {}; N = 0
for k in order:
    sh = shapes[k]; v = vis[k]; a = 0 if v is None else v[2].sum()
    if donor != '-': sh.nx, sh.ny = grid_for(sh.box, a, cell)
    off[k] = N; N += sh.nx * sh.ny if sh.nx else 1
rows, cols, vals = [], [], []
for k in order:
    sh, v = shapes[k], vis[k]
    if v is None: continue
    x0, y0, w = v; hh, ww = w.shape
    cy0, cy1 = max(y0, M), min(y0 + hh, M + H); cx0, cx1 = max(x0, M), min(x0 + ww, M + W)
    if cy1 <= cy0 or cx1 <= cx0: continue
    sub = w[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]; yy, xx = np.nonzero(sub > 1e-4)
    if len(yy) == 0: continue
    wt = sub[yy, xx]; py = yy + cy0 - M; px = xx + cx0 - M; pix = py * W + px
    if sh.nx:
        pi, vi, bw = bil_rows(sh.box, sh.nx, sh.ny, px + 0.5, py + 0.5)
        rows.append(pix[pi]); cols.append(off[k] + vi); vals.append(wt[pi] * bw)
    else:
        rows.append(pix); cols.append(np.full(len(pix), off[k])); vals.append(wt)
A = sparse.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(W * H, N)); A.sum_duplicates()
colsupp = np.asarray(A.sum(0)).ravel()
Rr, Rc, Rv = [], [], []; nr = 0
for k in order:
    sh = shapes[k]
    if not sh.nx: continue
    nx, ny = sh.nx, sh.ny; idx = off[k] + np.arange(nx * ny).reshape(ny, nx)
    c_ = ((sh.box[2] - sh.box[0]) / max(nx - 1, 1)) * ((sh.box[3] - sh.box[1]) / max(ny - 1, 1)); wgt = np.sqrt(lam_s * max(c_, 1.0))
    for a_, b_, d_ in [(idx[:, :-2], idx[:, 1:-1], idx[:, 2:]), (idx[:-2], idx[1:-1], idx[2:])]:
        a_, b_, d_ = a_.ravel(), b_.ravel(), d_.ravel(); m_ = len(a_)
        if m_ == 0: continue
        rr = nr + np.arange(m_); nr += m_
        Rr += [rr, rr, rr]; Rc += [a_, b_, d_]; Rv += [np.full(m_, wgt), np.full(m_, -2 * wgt), np.full(m_, wgt)]
    for a_, b_ in [(idx[:, :-1], idx[:, 1:]), (idx[:-1], idx[1:])]:
        a_, b_ = a_.ravel(), b_.ravel(); m_ = len(a_)
        if m_:
            rr = nr + np.arange(m_); nr += m_; wa = np.sqrt(lam_m * max(c_, 1.0))
            Rr += [rr, rr]; Rc += [a_, b_]; Rv += [np.full(m_, wa), np.full(m_, -wa)]
        lo_, hi_ = np.minimum(colsupp[a_], colsupp[b_]), np.maximum(colsupp[a_], colsupp[b_]); hid = lo_ < 0.5
        wm = np.sqrt(max(c_, 1.0)) * np.where(hi_ < 0.5, 0.5, 0.1)[hid]; a_, b_ = a_[hid], b_[hid]; m_ = len(a_)
        if m_ == 0: continue
        rr = nr + np.arange(m_); nr += m_
        Rr += [rr, rr]; Rc += [a_, b_]; Rv += [wm, -wm]
R = sparse.csr_matrix((np.concatenate(Rv), (np.concatenate(Rr), np.concatenate(Rc))), shape=(nr, N)) if nr else sparse.csr_matrix((0, N))
target = (ref - fixed).reshape(-1, 3)
AtR = A.T @ target
prior = np.zeros((N, 3)); ridge = np.full(N, 1e-3)
for k in order:
    s_ = slice(off[k], off[k] + (shapes[k].nx * shapes[k].ny if shapes[k].nx else 1)); tot = colsupp[s_].sum()
    prior[s_] = (A.T @ ref.reshape(-1, 3))[s_].sum(0) / tot if tot > 1e-6 else 0.5
    if tot < 40: ridge[s_] = 0.05 * max(tot / (s_.stop - s_.start), 0.5)
AtA = (A.T @ A + R.T @ R + sparse.diags(ridge)).tocsc()
X = np.clip(np.stack([spsolve(AtA, AtR[:, c] + ridge * prior[:, c]) for c in range(3)], 1), 0, 1)
for k in order:
    sh = shapes[k]; sh.cols = X[off[k]:off[k] + (sh.nx * sh.ny if sh.nx else 1)]
pred = np.clip(fixed + (A @ X).reshape(H, W, 3), 0, 1)
de = deltaE_ciede2000(rgb2lab(pred), rgb2lab(ref))
print('fitted %d shapes (%d unknowns); predicted dE00 mean %.3f p95 %.2f (%.0fs)' % (len(new), N, de.mean(), np.percentile(de, 95), time.time() - t0))
write(shapes, dst)
