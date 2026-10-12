"""Phase B stage 5: joint LSQ of all fills (flat or bilinear mesh over tight bounds) through the exact render model
(AA coverage + source-over stacking [+ optional PSF]); mesh smoothness; colour continuity across smooth boundaries."""
import sys, json, time, numpy as np
from scipy import sparse, ndimage as ndi
from scipy.sparse.linalg import spsolve
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000
import model
from model import M, WX, HX
from art import W, H, flatten, rasterize, LAYERS
from pbart import PShape, write, tight_bounds
SP = '/tmp/work/'
HARD, SOFT, SMOOTH = 0, 1, 2

def grid_for(box, area, h=16, nmax=96):
    bw, bh = box[2] - box[0], box[3] - box[1]
    if area < 12 or max(bw, bh) < 3: return 0, 0
    return int(np.clip(round(bw / h) + 1, 2, nmax)), int(np.clip(round(bh / h) + 1, 2, nmax))

def bil_rows(box, nx, ny, X, Y):
    """Bilinear weights -> (point idx, vertex idx, weight) arrays."""
    x0, y0, x1, y1 = box
    u = np.clip((X - x0) / max(x1 - x0, 1e-9), 0, 1) * (nx - 1); v = np.clip((Y - y0) / max(y1 - y0, 1e-9), 0, 1) * (ny - 1)
    i = np.minimum(u.astype(int), nx - 2); j = np.minimum(v.astype(int), ny - 2)
    fu, fv = u - i, v - j
    r = np.arange(len(X))
    return (np.repeat(r, 4), np.stack([j * nx + i, j * nx + i + 1, (j + 1) * nx + i, (j + 1) * nx + i + 1], 1).ravel(),
            np.stack([(1 - fu) * (1 - fv), fu * (1 - fv), (1 - fu) * fv, fu * fv], 1).ravel())

def visible_groups(shapes, covs):
    """Front-to-back transmittance with blurred runs (consecutive same-blur shapes in a layer = one blurred layer).
    Crisp shape k: vis[k] = (x0, y0, weight). Blurred shape k: vis[k] = (x0, y0, local weight), groups[k] = gid;
    ginfo[gid] = (X0, Y0, T_after patch, sigma)."""
    n = len(shapes); T = np.ones((HX, WX)); vis = [None] * n; grp = [-1] * n; ginfo = []
    i = n - 1
    while i >= 0:
        sh = shapes[i]
        if sh.blur > 0:
            j = i
            while j - 1 >= 0 and shapes[j - 1].blur == sh.blur and shapes[j - 1].layer == sh.layer: j -= 1
            idx = [k for k in range(j, i + 1) if covs[k] is not None]
            if idx:
                pad = int(np.ceil(4 * sh.blur)) + 2
                X0 = max(min(covs[k][0] for k in idx) - pad, 0); Y0 = max(min(covs[k][1] for k in idx) - pad, 0)
                X1 = min(max(covs[k][0] + covs[k][2].shape[1] for k in idx) + pad, WX); Y1 = min(max(covs[k][1] + covs[k][2].shape[0] for k in idx) + pad, HX)
                Tl = np.ones((Y1 - Y0, X1 - X0))
                for k in reversed(idx):
                    x0, y0, c = covs[k]; h, w = c.shape
                    sub = Tl[y0 - Y0:y0 - Y0 + h, x0 - X0:x0 - X0 + w]
                    vis[k] = (x0, y0, c * sub); grp[k] = len(ginfo)
                    sub *= (1 - c)
                A = ndi.gaussian_filter(1 - Tl, sh.blur, mode='constant', truncate=4)
                ginfo.append((X0, Y0, T[Y0:Y1, X0:X1].copy(), sh.blur))
                T[Y0:Y1, X0:X1] *= (1 - A)
            i = j - 1
        else:
            if covs[i] is not None:
                x0, y0, c = covs[i]; h, w = c.shape
                vis[i] = (x0, y0, c * T[y0:y0 + h, x0:x0 + w]); T[y0:y0 + h, x0:x0 + w] *= (1 - c)
            i -= 1
    return vis, grp, ginfo

def run(base, shapes_json, dst, lam_s=0.003, mu=4.0, psf=0.0, h=16):
    t0 = time.time()
    S = json.load(open(shapes_json))
    shapes = [PShape(s['layer'], pathstr=s['path'], blur=s['blur'], region=s['region']) for s in S]
    # draw order: the json is in draw order already; layer order must be preserved for the data files
    ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
    covs = model.coverage(shapes); vis, grp, ginfo = visible_groups(shapes, covs)
    area = np.array([0 if v is None else v[2][max(M - v[1], 0):, :].sum() for v in vis])
    # unknown layout
    import os
    cell = np.load(base + '_cell.npy') if os.path.exists(base + '_cell.npy') else None
    if cell is not None and max(sh.region for sh in shapes) >= len(cell):
        cell = np.concatenate([cell, np.full(max(sh.region for sh in shapes) + 1 - len(cell), 6.0)])
    off = [0]; dims = []
    for sh, v in zip(shapes, vis):
        a = 0 if v is None else v[2].sum()
        nx, ny = grid_for(sh.box, a, cell[sh.region] if cell is not None else h)
        sh.nx, sh.ny = nx, ny; dims.append((nx, ny))
        off.append(off[-1] + (nx * ny if nx else 1))
    N = off[-1]
    rows, cols, vals = [], [], []
    for k, (sh, v) in enumerate(zip(shapes, vis)):
        if v is None: continue
        if grp[k] >= 0:
            X0, Y0, Tp, sig = ginfo[grp[k]]
            x0, y0, w = v; hh, ww = w.shape
            ys_, xs_ = np.mgrid[y0:y0 + hh, x0:x0 + ww]
            if sh.nx:
                pi, vi, bw = bil_rows(sh.box, sh.nx, sh.ny, (xs_ + 0.5 - M).ravel(), (ys_ + 0.5 - M).ravel())
                Bm = sparse.csr_matrix((bw, (pi, vi)), shape=(hh * ww, sh.nx * sh.ny))
                basis_imgs = [(vtx, np.asarray(Bm[:, vtx].todense()).reshape(hh, ww) * w) for vtx in range(sh.nx * sh.ny)]
            else:
                basis_imgs = [(0, w)]
            for vtx, bimg in basis_imgs:
                if bimg.max() < 1e-6: continue
                big = np.zeros(Tp.shape); big[y0 - Y0:y0 - Y0 + hh, x0 - X0:x0 - X0 + ww] = bimg
                g = ndi.gaussian_filter(big, sig, mode='constant', truncate=4) * Tp
                cy0, cy1 = max(Y0, M), min(Y0 + Tp.shape[0], M + H); cx0, cx1 = max(X0, M), min(X0 + Tp.shape[1], M + W)
                if cy1 <= cy0 or cx1 <= cx0: continue
                gs = g[cy0 - Y0:cy1 - Y0, cx0 - X0:cx1 - X0]
                yy, xx = np.nonzero(gs > 1e-4)
                rows.append((yy + cy0 - M) * W + xx + cx0 - M); cols.append(np.full(len(yy), off[k] + vtx)); vals.append(gs[yy, xx])
            continue
        x0, y0, w = v; hh, ww = w.shape
        cy0, cy1 = max(y0, M), min(y0 + hh, M + H); cx0, cx1 = max(x0, M), min(x0 + ww, M + W)
        if cy1 <= cy0 or cx1 <= cx0: continue
        sub = w[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
        yy, xx = np.nonzero(sub > 1e-4)
        if len(yy) == 0: continue
        wt = sub[yy, xx]; py = yy + cy0 - M; px = xx + cx0 - M
        pix = py * W + px
        if sh.nx:
            pi, vi, bw = bil_rows(sh.box, sh.nx, sh.ny, px + 0.5, py + 0.5)
            rows.append(pix[pi]); cols.append(off[k] + vi); vals.append(wt[pi] * bw)
        else:
            rows.append(pix); cols.append(np.full(len(pix), off[k])); vals.append(wt)
    A = sparse.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(W * H, N))
    A.sum_duplicates()
    if psf > 0:
        pass  # TODO: PSF on columns
    # regularisers: mesh second differences (much stronger where vertices have no visible support), ridge
    colsupp = np.asarray(A.sum(0)).ravel()
    Rr, Rc, Rv = [], [], []; nr = 0
    for k, sh in enumerate(shapes):
        if not sh.nx: continue
        nx, ny = sh.nx, sh.ny; idx = off[k] + np.arange(nx * ny).reshape(ny, nx)
        cell = ((sh.box[2] - sh.box[0]) / max(nx - 1, 1)) * ((sh.box[3] - sh.box[1]) / max(ny - 1, 1))
        wgt = np.sqrt(lam_s * max(cell, 1.0))
        for a_, b_, c_ in [(idx[:, :-2], idx[:, 1:-1], idx[:, 2:]), (idx[:-2], idx[1:-1], idx[2:])]:
            a_, b_, c_ = a_.ravel(), b_.ravel(), c_.ravel(); m_ = len(a_)
            if m_ == 0: continue
            rr = nr + np.arange(m_); nr += m_
            Rr += [rr, rr, rr]; Rc += [a_, b_, c_]; Rv += [np.full(m_, wgt), np.full(m_, -2 * wgt), np.full(m_, wgt)]
        # hidden vertices: membrane (first differences) -> harmonic extension of visible neighbours, no overshoot
        for a_, b_ in [(idx[:, :-1], idx[:, 1:]), (idx[:-1], idx[1:])]:
            a_, b_ = a_.ravel(), b_.ravel()
            lo_, hi_ = np.minimum(colsupp[a_], colsupp[b_]), np.maximum(colsupp[a_], colsupp[b_])
            hid = lo_ < 0.5
            wm = np.sqrt(max(cell, 1.0)) * np.where(hi_ < 0.5, 0.5, 0.1)[hid]
            a_, b_ = a_[hid], b_[hid]; m_ = len(a_)
            if m_ == 0: continue
            rr = nr + np.arange(m_); nr += m_
            Rr += [rr, rr]; Rc += [a_, b_]; Rv += [wm, -wm]
    R = sparse.csr_matrix((np.concatenate(Rv), (np.concatenate(Rr), np.concatenate(Rc))), shape=(nr, N)) if nr else sparse.csr_matrix((0, N))
    # continuity across smooth boundaries (sampled at 1x boundary pixel pairs)
    reg = np.load(base + '_reg.npy'); P = np.load(base + '_pairs.npy')
    import os
    cont_classes = (SMOOTH, SOFT) if os.environ.get('PB_CONT_SOFT', '0') == '1' else (SMOOTH,)
    smooth = {(int(a), int(b)) for a, b, c, *_ in P if int(c) in cont_classes}
    blurred_regions = {sh.region for sh in shapes if sh.blur > 0}
    smooth = {p_ for p_ in smooth if p_[0] not in blurred_regions and p_[1] not in blurred_regions}
    by_region = {}
    for k, sh in enumerate(shapes): by_region.setdefault(sh.region, []).append(k)
    from regions import boundary_pairs
    y0_, x0_, y1_, x1_ = boundary_pairs(reg)
    ra, rb = reg[y0_, x0_], reg[y1_, x1_]
    keep = np.array([(min(a, b), max(a, b)) in smooth for a, b in zip(ra, rb)])
    Cr, Cc, Cv = [], [], []; nc = 0
    sel = np.nonzero(keep)[0][::2]
    for i in sel:
        X = (x0_[i] + x1_[i]) / 2 + 0.5; Y = (y0_[i] + y1_[i]) / 2 + 0.5
        terms = []
        for rr_, sign in ((ra[i], 1.0), (rb[i], -1.0)):
            ks = [k for k in by_region.get(int(rr_), []) if shapes[k].box[0] - 1 <= X <= shapes[k].box[2] + 1 and shapes[k].box[1] - 1 <= Y <= shapes[k].box[3] + 1]
            if not ks: break
            k = ks[0]; sh = shapes[k]
            if sh.nx:
                pi, vi, bw = bil_rows(sh.box, sh.nx, sh.ny, np.array([X]), np.array([Y]))
                terms += [(off[k] + vi, sign * bw)]
            else:
                terms += [(np.array([off[k]]), np.array([sign]))]
        if len(terms) != 2: continue
        for ci, cv in terms:
            Cr.append(np.full(len(ci), nc)); Cc.append(ci); Cv.append(cv * np.sqrt(mu))
        nc += 1
    C = sparse.csr_matrix((np.concatenate(Cv), (np.concatenate(Cr), np.concatenate(Cc))), shape=(nc, N)) if nc else sparse.csr_matrix((0, N))
    # ridge toward per-shape mean reference colour (keeps unsupported vertices sane)
    prior = np.zeros((N, 3)); colsum = np.asarray(A.sum(0)).ravel()
    AtR = A.T @ ref.reshape(-1, 3)
    for k, sh in enumerate(shapes):
        s_ = slice(off[k], off[k + 1]); tot = colsum[s_].sum()
        prior[s_] = AtR[s_].sum(0) / tot if tot > 1e-6 else 0.5
    ridge = np.full(N, 1e-3)
    for k, sh in enumerate(shapes):          # small/flat shapes: pull toward their sampled reference colour
        tot = colsum[off[k]:off[k + 1]].sum()
        if tot < 40: ridge[off[k]:off[k + 1]] = 0.05 * max(tot / (off[k + 1] - off[k]), 0.5)
    for k, sh in enumerate(shapes):          # blurred shapes: stronger pull to their reference colour
        if sh.blur > 0: ridge[off[k]:off[k + 1]] = 0.2 * max(colsum[off[k]:off[k + 1]].mean(), 1.0)
    AtA = (A.T @ A + R.T @ R + C.T @ C + sparse.diags(ridge)).tocsc()
    X = np.stack([spsolve(AtA, AtR[:, c] + ridge * prior[:, c]) for c in range(3)], 1)
    X = np.clip(X, 0, 1)
    for k, sh in enumerate(shapes):
        sh.cols = X[off[k]:off[k + 1]]
    pred = np.clip((A @ X).reshape(H, W, 3), 0, 1)
    de = deltaE_ciede2000(rgb2lab(pred), rgb2lab(ref))
    print('shapes %d, unknowns %d, continuity rows %d; predicted dE00 mean %.3f p95 %.2f (%.0fs)' % (len(shapes), N, nc, de.mean(), np.percentile(de, 95), time.time() - t0))
    # data files: per layer, in draw order
    write(shapes, dst)
    return pred

if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2], sys.argv[3])
