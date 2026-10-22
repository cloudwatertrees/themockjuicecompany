"""Variant "join": A's right bank continues down beside the path and merges into B's mushroom-island cliff.

usage: make.py            (rebuilds vb_join/B_seam.png and vb_join/edits.npz from ../A.png and ../base/B_warp.png)

Edits (all translation / small-scale clones of the art's own pixels, colour-matched at their edges, short feathers):
  bank     A's bank (last 200 rows, straightened along its edges) quilted along the new bank course e(y)..o(y), width
           easing 75 -> 26 px; inner (path-side) and outer (scalloped) halves are separate layers joined by a min-error
           seam that avoids pebbles, so the bank narrows without squashing pebbles. The verge (pale lip + grass) rides
           on the outer layer. Ends in a min-error cut into B's own cliff.
  stone    the stepping stone cut by A's bottom edge on the path gets its lower half from another A stone.
  left     A's bottom band (bushes, boulder, grass) continued by quilted A patches, cut into B's canopy.
  boulder  the boulder's lower arc (texture translated from its lower body, edge profile from its visible right rim)
           with a soft contact shadow.
  pine     A's large pine closed by the lower tier of A's left pine (translated, scaled), cut into B's bushes.
  seam     per-column low-frequency offset at the seam row plus a 4-row feather of the residual.
"""
import os
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import (gaussian_filter, gaussian_filter1d, map_coordinates, distance_transform_edt,
                           binary_dilation, binary_erosion, median_filter)

HERE = os.path.dirname(os.path.abspath(__file__))
SEAM = os.path.dirname(HERE)
ROOT = os.path.dirname(SEAM)
W, H = 937, 1678
LUM = np.array([0.299, 0.587, 0.114])
DBG = os.environ.get('DBG')


def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float64)


def lum(img):
    return img @ LUM


def save(img, p):
    Image.fromarray(np.clip(np.round(img), 0, 255).astype(np.uint8)).save(p)


def feather(mask, r):
    """Binary mask -> alpha with a soft edge of total width ~2r centred on the mask boundary."""
    m = mask.astype(bool)
    sd = distance_transform_edt(m) - distance_transform_edt(~m)
    return np.clip(0.5 + sd / (2.0 * r), 0, 1)


def hermite(t, p0, p1, m0, m1):
    t = np.clip(t, 0, 1)
    h00 = 2 * t ** 3 - 3 * t ** 2 + 1; h10 = t ** 3 - 2 * t ** 2 + t
    h01 = -2 * t ** 3 + 3 * t ** 2; h11 = t ** 3 - t ** 2
    return h00 * p0 + h10 * m0 + h01 * p1 + h11 * m1


def seam_dp(cost, lo, hi, step=1, start=None):
    """Vertical seam through cost[y, x]: one x per row, x in [lo[y], hi[y]], |dx| <= step. Returns x per row."""
    Hc, Wc = cost.shape
    big = 1e12
    c = np.full((Hc, Wc), big)
    for y in range(Hc):
        c[y, int(lo[y]):int(hi[y]) + 1] = cost[y, int(lo[y]):int(hi[y]) + 1]
    if start is not None:
        keep = c[0, int(start)]; c[0] = big; c[0, int(start)] = keep
    acc = c[0].copy(); back = np.zeros((Hc, Wc), np.int16)
    for y in range(1, Hc):
        best = np.full(Wc, big); arg = np.zeros(Wc, np.int16)
        for s in range(-step, step + 1):
            sh = np.full(Wc, big)
            if s > 0:
                sh[s:] = acc[:-s]
            elif s < 0:
                sh[:s] = acc[-s:]
            else:
                sh = acc.copy()
            sh = sh + 0.15 * abs(s)
            b = sh < best
            best[b] = sh[b]; arg[b] = s
        acc = best + c[y]; back[y] = arg
    xs = np.zeros(Hc, int); xs[-1] = int(np.argmin(acc))
    for y in range(Hc - 1, 0, -1):
        xs[y - 1] = xs[y] - back[y, xs[y]]
    return xs




# ----------------------------------------------------------------------------------------------------------------
# canvas: A's last PAD rows stacked on B's top NB rows, so A is the outside neighbour of every edit's top edge

PAD, NB = 40, 500


def ring_means(img, ring, sigma):
    m = ring.astype(float)
    den = gaussian_filter(m, sigma)
    mu = np.stack([gaussian_filter(img[..., c] * m, sigma) for c in range(3)], -1) / np.maximum(den, 1e-9)[..., None]
    return mu, den


def edge_match(patch, base, mask, sigma=4.0, reach=9.0, contrast=True, dmax=22.0):
    """Shift (and gently rescale) `patch` so its local mean/contrast just inside `mask` matches `base` just outside,
    with the correction decaying inward over `reach` px. Works on the canvas (A rows count as outside)."""
    inside = mask.astype(bool)
    ring_o = binary_dilation(inside, iterations=3) & ~inside
    ring_i = inside & ~binary_erosion(inside, iterations=3)
    mb, db = ring_means(base, ring_o, sigma)
    mp, dp = ring_means(patch, ring_i, sigma)
    ok = (db > 0.02) & (dp > 0.02)
    ok &= np.abs(lum(mb - mp)) < dmax               # object edges (bush against bank) are not seams: skip them
    D = np.where(ok[..., None], mb - mp, 0)
    v = (ok & ring_i).astype(float)
    Df = np.stack([gaussian_filter(D[..., c] * v, 3) for c in range(3)], -1) / np.maximum(gaussian_filter(v, 3), 1e-9)[..., None]
    have = gaussian_filter(v, 3) > 1e-3
    depth = distance_transform_edt(inside)
    wdec = np.exp(-np.maximum(depth - 1, 0) / reach) * have
    out = patch.copy()
    if contrast:
        # contrast: ratio of local std on both sides of the edge, clipped, applied around the local patch mean
        lb, lp = lum(base), lum(patch)
        def lstd(L, ring, mu):
            m = ring.astype(float); den = gaussian_filter(m, 6)
            e2 = gaussian_filter(L * L * m, 6) / np.maximum(den, 1e-9)
            e1 = gaussian_filter(L * m, 6) / np.maximum(den, 1e-9)
            return np.sqrt(np.maximum(e2 - e1 ** 2, 0)), den
        sb, d1 = lstd(lb, ring_o, None); sp, d2 = lstd(lp, ring_i, None)
        k = np.where((d1 > 0.02) & (d2 > 0.02), np.clip((sb + 1) / (sp + 1), 0.8, 1.25), 1.0)
        kv = (k - 1) * v
        kf = 1 + gaussian_filter(kv, 3) / np.maximum(gaussian_filter(v, 3), 1e-9)
        kf = 1 + (kf - 1) * wdec
        pv = (binary_dilation(inside, iterations=6) & (patch.sum(-1) > 0)).astype(float)
        mloc = np.stack([gaussian_filter(patch[..., c] * pv, 3) for c in range(3)], -1) / np.maximum(gaussian_filter(pv, 3), 1e-9)[..., None]
        out = mloc + (patch - mloc) * kf[..., None]
    return out + Df * wdec[..., None]


def composite(C, patch, mask, r=2.5, reach=9.0, contrast=True):
    """Blend `patch` into canvas C over boolean `mask` (canvas coords): edge-matched, feathered (total ~2r px).
    The top edge against A's rows is not feathered (A is fixed); it is matched by the colour offset only.
    Returns new canvas and the alpha (canvas coords)."""
    m = mask.copy(); m[:PAD] = False
    pm = edge_match(patch, C, m, reach=reach, contrast=contrast)
    fm = m.copy()
    cols = m[PAD]
    fm[:PAD] |= cols[None, :]                       # feather as if the edit continued up into A
    alpha = feather(fm, r); alpha[:PAD] = 0
    alpha = np.where(m | (alpha > 0), alpha, 0)
    out = C + alpha[..., None] * (pm - C)
    return out, alpha


# ----------------------------------------------------------------------------------------------------------------
# bank

def brown(img):
    r, g = img[..., 0], img[..., 1]
    return (r - g > 22) & (r < 225) & (g < 200)


def cream(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    return (r > 215) & (g > 190) & (b > 160) & (r >= g) & (r - b < 75)


def a_bank_edges(A, n=200):
    """A's bank inner (path side) and outer (verge side) edge x per row, rows H-n..H-1, smoothed."""
    ys = np.arange(H - n, H)
    e, o = [], []
    for y in ys:
        idx = np.flatnonzero(brown(A[y, 600:800]))
        runs = np.split(idx, np.flatnonzero(np.diff(idx) > 3) + 1)
        r = max(runs, key=len)
        e.append(r[0] + 600); o.append(r[-1] + 601)
    e = gaussian_filter1d(np.array(e, float), 4, mode='nearest')
    o = gaussian_filter1d(np.array(o, float), 4, mode='nearest')
    return ys.astype(float), e, o


class Curve:
    """x = f(y) sampled on integer y; arclength and nearest-point projection (u: signed normal distance, + right)."""
    def __init__(self, y, x):
        self.y = np.asarray(y, float); self.x = np.asarray(x, float)
        self.d = np.gradient(self.x, self.y)
        self.s = np.concatenate([[0], np.cumsum(np.sqrt(1 + ((self.d[1:] + self.d[:-1]) / 2) ** 2))])

    def at(self, y):
        return np.interp(y, self.y, self.x), np.interp(y, self.y, self.d)

    def project(self, px, py, it=5):
        y0 = np.asarray(py, float).copy()
        for _ in range(it):
            x0, d0 = self.at(y0)
            y0 = np.clip(y0 + ((px - x0) * d0 + (py - y0)) / (1 + d0 ** 2), self.y[0], self.y[-1])
        x0, d0 = self.at(y0)
        u = ((px - x0) - d0 * (py - y0)) / np.sqrt(1 + d0 ** 2)
        return u, np.interp(y0, self.y, self.s)

    def point(self, v):
        y0 = np.interp(v, self.s, self.y)
        x0, d0 = self.at(y0)
        return x0, y0, d0


WA = 75.0          # straightened bank width (normal direction)
JL, JR = -18, 102  # strip columns: j = 0 inner edge, j = WA outer edge


def straighten(A, ys, e, o):
    """S[v, j]: A's bank resampled along the normals of its inner edge (unit arclength rows): inner edge at j = 0,
    outer edge at j = WA (small scale inside the bank only, unit scale outside)."""
    ci, co = Curve(ys, e), Curve(ys, o)
    v = np.arange(int(ci.s[-1]), dtype=float)
    x0, y0, d0 = ci.point(v)
    nx, ny = 1 / np.sqrt(1 + d0 ** 2), -d0 / np.sqrt(1 + d0 ** 2)
    wn = -co.project(x0, y0)[0]
    js = np.arange(JL, JR, dtype=float)[None]
    jj = np.where(js < 0, js, np.where(js > WA, wn[:, None] + js - WA, js * wn[:, None] / WA))
    px = x0[:, None] + jj * nx[:, None]; py = y0[:, None] + jj * ny[:, None]
    return np.stack([map_coordinates(A[..., c], [py, px], order=3, mode='nearest') for c in range(3)], -1)


def pebbles(S):
    L = lum(S)
    a, b = -JL + 4, -JL + int(WA) - 4
    band = L[:, a:b]
    med = median_filter(band, size=(31, 31))
    pm = np.zeros(L.shape, bool)
    pm[:, a:b] = (band - med > 4) | (band - med < -8)
    from scipy.ndimage import binary_opening
    return binary_dilation(binary_opening(pm, iterations=1), iterations=5)


def quilt_strip(S, P, T, first_cost, n_valid, ov=12, maxlen=58, keep_away=110, pre=12, avoid=(),
                free_from=None, vis_cols=None):
    """Quilt T rows from S along v. Chunk 1 (strip rows 0..) starts at the S row minimising `first_cost` (seam
    continuity with A, measured in target space) and must lie >= keep_away rows above A's last rows; later chunks
    overlap the previous by `ov` rows and join on a min-error seam that never cuts a pebble. Chunks avoid source rows
    already used (by this strip or listed in `avoid`, e.g. the other layer's strip) so pebble arrangements are not
    repeated; from strip row `free_from` on, chunks are also scored by their pebble content in `vis_cols` (the narrow
    bank near the cliff has no room for whole pebbles)."""
    n, wj = S.shape[:2]
    n = n_valid
    L = lum(S)
    out = np.zeros((T, wj, 3)); pout = np.zeros((T, wj), bool)
    fit, v0 = min((first_cost(v), v) for v in range(0, n - keep_away - pre))
    length = min(maxlen + pre, T)
    out[:length] = S[v0:v0 + length]; pout[:length] = P[v0:v0 + length]
    chunks = [(0, v0, length)]; used = [(v0, v0 + length)]
    t = length
    blocked = list(avoid)
    pc = None
    if vis_cols is not None:
        pc = np.concatenate([[0], np.cumsum(P[:, vis_cols].mean(1))])
    while t < T:
        prev = lum(out[t - ov:t])
        length = min(maxlen, T - t)
        cand = []
        for s_ in range(ov, n - 20):
            if any(a - 30 < s_ and s_ - ov < b + 30 for a, b in used + blocked):
                continue
            sc = np.abs(L[s_ - ov:s_] - prev).mean()
            if free_from is not None and t + length > free_from and pc is not None:
                e_ = min(n, s_ + length)
                sc += 60 * (pc[e_] - pc[s_]) / max(1, e_ - s_)
            cand.append((sc, s_))
        if not cand:
            if blocked:
                blocked = []
            else:
                used = used[-1:]
            continue
        d, s_ = min(cand)
        length = min(maxlen, n - s_, T - t)
        qc = np.abs(L[s_ - ov:s_] - prev) + 50 * (P[s_ - ov:s_] | pout[t - ov:t])     # never cut through a pebble
        xs = seam_dp(qc.T, np.zeros(wj), np.full(wj, ov - 1))
        for j in range(wj):
            r = xs[j]
            out[t - ov + r:t, j] = S[s_ - ov + r:s_, j]; pout[t - ov + r:t, j] = P[s_ - ov + r:s_, j]
        out[t:t + length] = S[s_:s_ + length]; pout[t:t + length] = P[s_:s_ + length]
        chunks.append((t, s_, length)); used.append((s_ - ov, s_ + length))
        t += length
    return out, pout, chunks, fit, used


def bank_course(ea, oa, YJ, T, ej, oj):
    """Inner/outer edge x for y in [-40, T]: Hermite from A's end (with its end slope) to the cliff (slope 0)."""
    y = np.arange(-40, T + 1, dtype=float)
    se = (ea[-1] - ea[-11]) / 10 * YJ
    so = (oa[-1] - oa[-11]) / 10 * YJ
    e = hermite(y / YJ, ea[-1], ej, se, 0.0)
    o = hermite(y / YJ, oa[-1], oj, so, 0.0)
    e[y > YJ] = ej; o[y > YJ] = oj
    e[y < 0] = ea[-1] + se / YJ * y[y < 0]; o[y < 0] = oa[-1] + so / YJ * y[y < 0]
    return y, e, o


def cliff_profile(Bw, ej, oj, rows):
    """B's cliff mean colour per strip column j (inner side x = ej + j, outer side x = oj + j - WA, body between)."""
    prof = np.zeros((JR - JL, 3))
    seg = Bw[rows[0]:rows[1]]
    def col(x):
        return np.stack([np.interp(x, np.arange(W), seg[..., c].mean(0)) for c in range(3)], -1)
    body = np.mean([col(ej + k) for k in range(7, 20)], 0)
    grass = np.mean([col(oj + k) for k in range(3, 12)], 0)
    for i, j in enumerate(range(JL, JR)):
        if j <= 20:
            prof[i] = col(ej + j)
        elif j >= WA - 20:
            k = j - WA
            prof[i] = col(oj + k) if k <= 10 else grass
        else:
            prof[i] = body
    return prof


def build_bank(A, Bw, YJ=185, G=24, T=222):
    ej, oj = 607.0, 633.5
    ys, ea, oa = a_bank_edges(A, n=280)
    S = straighten(A, ys, ea, oa)
    Pm = pebbles(S)
    yc, e, o = bank_course(ea, oa, YJ, T, ej, oj)
    ci, co = Curve(yc, e), Curve(yc, o)
    vb_i, vb_o = np.interp(0, yc, ci.s), np.interp(0, yc, co.s)
    PRE = 12
    Ts = int(max(ci.s[-1] - vb_i, co.s[-1] - vb_o)) + 4 + PRE
    # seam continuity of a strip start vs A's last 6 rows, rendered through the target mapping (rows -6..-1)
    ty, tx = np.mgrid[-6:0, 640:772].astype(float)
    tu, tv = ci.project(tx, ty); tv = tv - vb_i + PRE
    keep = (tu >= JL + 3) & (tu <= (oa[-1] - ea[-1]) + G)
    tA = lum(A[H - 6:H, 640:772])
    tw = np.linspace(0.4, 1.0, 6)[:, None] * keep
    LS = lum(S)
    def first_cost(vs):
        r = map_coordinates(LS, [vs + tv, tu - JL], order=1, mode='nearest')
        return float((np.abs(r - tA) * tw).sum() / tw.sum())
    vY = lambda y: np.interp(y, yc, ci.s) - vb_i + PRE
    jcol = lambda j: int(round(j - JL))
    vin = np.r_[jcol(-6):jcol(22)]; vout = np.r_[jcol(WA - 24):jcol(WA + 4)]
    # outer-layer seam continuity (rows -6..-1 through the outer curve)
    to_u, to_v = co.project(tx, ty); to_v = to_v - vb_o + PRE
    def first_cost_o(vs):
        r = map_coordinates(LS, [vs + to_v, to_u + WA - JL], order=1, mode='nearest')
        return float((np.abs(r - tA) * tw).sum() / tw.sum())
    Q, Qp, chunks, fit, used_i = quilt_strip(S, Pm, Ts, first_cost, len(S) - 12, pre=PRE, maxlen=34,
                                             free_from=int(vY(100)), vis_cols=vin)
    Qo, Qop, chunks_o, fit_o, _ = quilt_strip(S, Pm, Ts, first_cost_o, len(S) - 12, pre=PRE, maxlen=34,
                                              avoid=used_i[1:], free_from=int(vY(100)), vis_cols=vout)
    chunks = dict(inner=chunks, outer=chunks_o)
    # colour ramp toward B's cliff (means per strip column, texture kept; bank-body contrast eased to the cliff's),
    # from y ~ 95 to y ~ YJ - 8
    prof = cliff_profile(Bw, ej, oj, (188, 208))
    t = np.clip((np.arange(Ts) - vY(95)) / (vY(YJ - 8) - vY(95)), 0, 1)
    t = t * t * (3 - 2 * t)
    sB = lum(Bw[188:208, 612:629]).std()
    def ramp(Q):
        muQ = np.stack([gaussian_filter1d(Q[..., c], 14, axis=0, mode='nearest') for c in range(3)], -1)
        muQ = np.stack([gaussian_filter1d(muQ[..., c], 1.5, axis=1, mode='nearest') for c in range(3)], -1)
        body = slice(jcol(3), jcol(WA - 3))
        r0, r1 = int(vY(110)), int(vY(YJ))
        sQ = lum(Q[r0:r1, body] - muQ[r0:r1, body]).std()
        k = np.ones(Q.shape[1]); k[body] = np.clip(sB / max(sQ, 1e-6), 0.5, 1.0)
        kk = 1 + t[:, None] * (k[None] - 1)
        return muQ + (Q - muQ) * kk[..., None] + t[:, None, None] * (prof[None] - muQ)
    Q = ramp(Q); Qo = ramp(Qo)
    # target pixels -> strip coordinates through each layer
    yy, xx = np.mgrid[0:T, 0:W].astype(float)
    ui, vi = ci.project(xx, yy); vi = vi - vb_i + PRE
    uo, vo = co.project(xx, yy); vo = vo - vb_o + PRE
    vrow = np.arange(Ts, dtype=float)
    px, py, _ = ci.point(vrow + vb_i - PRE)
    wn = -co.project(px, py)[0]
    # inner/outer layer seam c(v): min error between layers, never through a pebble
    Lq = lum(Q); Lqo = lum(Qo); j0 = -JL
    cost = np.zeros((Ts, JR - JL)); lo = np.zeros(Ts); hi = np.zeros(Ts)
    for r in range(Ts):
        sh = int(round(WA - wn[r]))
        cost[r] = np.abs(Lq[r] - np.roll(Lqo[r], -sh)) + 80 * (Qp[r] | np.roll(Qop[r], -sh))
        lo[r] = j0 + 7; hi[r] = j0 + max(8, int(wn[r]) - 9)
    cseam = seam_dp(cost, lo, hi) - j0
    cat = np.interp(vi, vrow, cseam)
    use_in = ui < cat
    vv = np.where(use_in, vi, vo)
    jj = np.where(use_in, ui, uo + WA) - JL
    lay_in = np.stack([map_coordinates(Q[..., c], [vi, ui - JL], order=3, mode='nearest') for c in range(3)], -1)
    lay_out = np.stack([map_coordinates(Qo[..., c], [vo, uo + WA - JL], order=3, mode='nearest') for c in range(3)], -1)
    wl = np.clip((cat - ui) / 2.0 + 0.5, 0, 1)[..., None]       # 2 px feather between the two layers
    comp = wl * lay_in + (1 - wl) * lay_out
    reg = (ui >= JL + 3) & (uo <= G) & (vv >= 0)
    return comp, reg, dict(ui=ui, uo=uo, chunks=chunks, fit=fit, YJ=YJ, T=T, e=np.interp(np.arange(T), yc, e),
                           o=np.interp(np.arange(T), yc, o), G=G)


def bank_mask(comp, reg, info, Bw):
    """Edit mask (B coords, rows < T): region minus (a) what lies below a min-error cut into B's cliff and (b) what
    lies right of a min-error cut into B's grass on the verge side. B's bush pixels on the verge stay in front."""
    T, G = info['T'], info['G']
    uo = info['uo']
    Bt = Bw[:T]
    diff = np.abs(comp - Bt).mean(-1)
    grad = np.hypot(*np.gradient(lum(Bt)))
    m = reg.copy()
    # (a) bottom cut: one row per column, rows 168..T-3, through low difference / flat areas
    y0, y1 = 168, T - 3
    cols = np.flatnonzero(reg[y0:y1].any(0))
    xa, xb = cols.min(), cols.max() + 1
    cost = (diff + 0.5 * grad)[y0:y1, xa:xb]
    rows = seam_dp(cost.T, np.zeros(xb - xa), np.full(xb - xa, y1 - y0 - 1), step=1) + y0
    for i, x in enumerate(range(xa, xb)):
        m[rows[i]:, x] = False
    # (b) verge cut: per row a column within uo in [9, G], right of any B cream pixel, through low difference
    cr = cream(Bt)
    lo = np.zeros(T); hi = np.zeros(T)
    for y in range(T):
        band = np.flatnonzero((uo[y] >= 9) & (uo[y] <= G) & reg[y])
        if band.size == 0:
            lo[y] = hi[y] = 0; continue
        c = np.flatnonzero(cr[y, band.min():band.max() + 1] & (uo[y, band.min():band.max() + 1] > 0))
        lo[y] = band.min() if c.size == 0 else min(band.max(), band.min() + c.max() + 3)
        hi[y] = band.max()
    cost = diff + 0.5 * grad
    valid = np.flatnonzero(hi > 0)
    ya, yb = valid.min(), valid.max() + 1
    xs = np.zeros(T, int)
    xs[ya:yb] = seam_dp(cost[ya:yb], lo[ya:yb], np.maximum(hi, lo)[ya:yb], step=3)
    for y in range(ya, yb):
        m[y, xs[y] + 1:] &= ~(uo[y, xs[y] + 1:] > 0)
    # B's dark bushes overlapping the verge stay in front
    r, g, b = Bt[..., 0], Bt[..., 1], Bt[..., 2]
    bush = (g - r > 40) & (b - r > 5) & (lum(Bt) < 165) & (uo > -25) & (np.arange(T)[:, None] < 150)
    bush = binary_erosion(binary_dilation(bush, iterations=1), iterations=1)
    from scipy.ndimage import label
    lab, n = label(bush)
    sizes = np.bincount(lab.ravel())
    top = np.zeros(n + 1, bool); top[np.unique(lab[:8])] = True     # bushes cut by B's top edge are not kept
    bush = (sizes[lab] > 200) & (lab > 0) & ~top[lab]
    bush &= reg
    m &= ~bush
    return m, rows, xs, bush


# ----------------------------------------------------------------------------------------------------------------
# continuation clones (seam-matched translations of A)

def find_continuation(A, x0, x1, K, ctx=6, dx=40, dymin=60, dymax=900, extra_cost=None, src=None, src_rows=None):
    """Best translation (sx, sy) so that A[sy-ctx:sy, sx:sx+(x1-x0)] matches A's last ctx rows over x0..x1;
    the patch is then A[sy:sy+K, sx:sx+(x1-x0)] placed at B rows 0..K-1. Only sources at least `dymin` rows above
    the seam (sy <= H - dymin) are considered so the clone is not the rows right above it."""
    import cv2
    w = x1 - x0
    tpl = A[H - ctx:H, x0:x1].astype(np.float32)
    wts = np.repeat(np.linspace(0.35, 1.0, ctx)[:, None], w, 1).astype(np.float32)
    wts = np.repeat(wts[..., None], 3, -1)
    S_ = A if src is None else src
    if src_rows is None:
        ya = max(0, H - dymax - ctx); yb = H - dymin
    else:
        ya, yb = src_rows
    xa = max(0, x0 - dx); xb = min(W, x1 + dx)
    img = S_[ya:yb + ctx, xa:xb].astype(np.float32)          # template rows end at sy (exclusive) <= yb
    res = cv2.matchTemplate(img, tpl, cv2.TM_SQDIFF, mask=wts)
    res = res / (wts.sum())
    # source top of template at row ya + i; patch starts at sy = ya + i + ctx and needs K rows below
    nrow = res.shape[0]
    sy_all = ya + np.arange(nrow) + ctx
    res[sy_all + K > S_.shape[0]] = np.inf
    if extra_cost is not None:
        res = res + extra_cost(sy_all[:, None], xa + np.arange(res.shape[1])[None])
    i, j = np.unravel_index(np.argmin(res), res.shape)
    return xa + j, ya + i + ctx, float(np.sqrt(res[i, j]))


def cut_below(patch, base, region, ylo, yhi, wgrad=0.5, step=1):
    """Within `region` (B coords), keep rows above a min-error horizontal cut placed in rows [ylo(x), yhi(x)]."""
    diff = np.abs(patch - base).mean(-1)
    grad = np.hypot(*np.gradient(lum(base)))
    cols = np.flatnonzero(region.any(0))
    xa, xb = cols.min(), cols.max() + 1
    cost = (diff + wgrad * grad)[:, xa:xb].T                 # (x, y)
    lo = np.asarray(ylo)[xa:xb] if np.ndim(ylo) else np.full(xb - xa, ylo)
    hi = np.asarray(yhi)[xa:xb] if np.ndim(yhi) else np.full(xb - xa, yhi)
    rows = seam_dp(cost, lo, hi, step=step)
    m = region.copy()
    for i, x in enumerate(range(xa, xb)):
        m[rows[i]:, x] = False
    return m, rows, xa


def cut_left(patch, base, region, xlo, xhi, y0, y1, wgrad=0.5, step=1):
    """Within `region`, drop pixels left of a min-error vertical cut placed in columns [xlo, xhi] for rows y0..y1."""
    diff = np.abs(patch - base).mean(-1)
    grad = np.hypot(*np.gradient(lum(base)))
    cost = (diff + wgrad * grad)[y0:y1]
    xs = seam_dp(cost, np.full(y1 - y0, xlo), np.full(y1 - y0, xhi), step=step)
    m = region.copy()
    for i, y in enumerate(range(y0, y1)):
        m[y, :xs[i]] = False
    return m, xs


def shifted(A, sx, sy, x0, K):
    """Patch (B coords, rows 0..K-1, full width) = A translated so A[sy, sx] lands on B[0, x0]."""
    out = np.zeros((K, W, 3))
    xs = np.arange(W) + (sx - x0)
    ok = (xs >= 0) & (xs < W)
    out[:, ok] = A[sy:sy + K][:, xs[ok]]
    return out, ok


# ----------------------------------------------------------------------------------------------------------------
# pine: A's large pine continues one tier into B (its own tier edge, translated down), over B's dark bushes

def build_pine(A, Cb, K=60, src=(12, -111)):
    """Cb: current B (rows 0..K-1). Returns patch, mask (B coords, K rows), info."""
    x0, x1 = 748, 937
    # source: the same pine one tier higher (its tier edge = tips over the darker body below), shifted 12 px right so
    # its left edge meets A's pine edge at the seam (chosen by eye from the best seam matches; the free search prefers
    # tierless sources). Columns the shifted source cannot reach (beyond x ~925, off the phone frame) take the same
    # rows unshifted, joined on a min-error vertical cut.
    if src is None:
        sx, sy, fit = find_continuation(A, x0, 900, K, ctx=6, dx=45, dymin=85, dymax=200)
    else:
        sx, sy = x0 + src[0], H + src[1]
        fit = float(np.sqrt((((A[H - 6:H, x0:900] - A[sy - 6:sy, sx:sx + 900 - x0]) ** 2).mean())))
    patch, ok = shifted(A, sx, sy, x0, K)
    p2, _ = shifted(A, x0, sy, x0, K)
    d = np.abs(patch - p2).mean(-1)[:, 860:int(np.flatnonzero(ok).max())]
    xs2 = seam_dp(d, np.zeros(K), np.full(K, d.shape[1] - 1), step=1) + 860
    for y in range(K):
        patch[y, xs2[y]:] = p2[y, xs2[y]:]
    region = np.zeros((K, W), bool); region[:, x0:x1] = True
    # bottom cut into B's bushes / grass, rows 16..K-4
    m, rows, xa = cut_below(patch, Cb[:K], region, 16, K - 4, wgrad=1.5)
    # left cut into the (already edited) verge, columns x0+2..x0+26
    m, xs = cut_left(patch, Cb[:K], m, x0 + 2, x0 + 26, 0, K, wgrad=1.5)
    return patch, m, dict(sx=sx, sy=sy, fit=fit, rows=rows, xs=xs)


# ----------------------------------------------------------------------------------------------------------------
# stepping stone on the path, cut by A's bottom edge: its rim continues from another A stone (translated)

def build_stone(A, Cb, K=16, x0=530, x1=630, src=(-110, -136), scale=0.9, anchor=562):
    """The stepping stone cut by A's bottom edge: its rims converge ~2 px/row and A's last row still shows a 34 px
    gap between them (x 565..599). The stone at A (x ~435..495, y H-150..H-131) has the same gap on its row H-137,
    so its rows from H-136 on (translated by -110 px, 136 rows) close the cut stone. Its right rim sits ~4 px left
    of A's, so the source is sampled at 0.9 source px per target px around the left rim (x 562): a 10% widening."""
    sx, sy = x0 + src[0], H + src[1]
    xs = sx + (anchor - x0) + (np.arange(W) - anchor) * scale
    ys = np.arange(sy, sy + K, dtype=float)
    patch = np.stack([map_coordinates(A[..., c], [np.repeat(ys[:, None], W, 1), np.repeat(xs[None], K, 0)],
                                      order=1, mode='nearest') for c in range(3)], -1)
    region = np.zeros((K, W), bool); region[:, x0:x1] = True
    m, rows, xa = cut_below(patch, Cb[:K], region, 5, K - 2, wgrad=1.0)
    return patch, m, dict(sx=sx, sy=sy, fit=float(np.abs(lum(patch[0, x0:x1]) - lum(A[H - 1, x0:x1])).mean()))


# ----------------------------------------------------------------------------------------------------------------
# left: A's bushes and grass verge continue a few rows into B, then B's canopy resumes along its own leaf outlines

def grassy(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    return (g > r - 12) & (r > 150) & (b < r - 35) & (g > 170)


def find_grass_continuation(A, x0, x1, K, ctx=6, dx=70, px0=None, px1=None, ntop=400):
    """Like find_continuation, but the K rows below the match (over target columns px0..px1) must be grass only, so
    no object is duplicated. Scores the `ntop` best template matches by fit + 80 * non-grass fraction."""
    import cv2
    px0 = x0 if px0 is None else px0; px1 = x1 if px1 is None else px1
    tpl = A[H - ctx:H, x0:x1].astype(np.float32)
    res = cv2.matchTemplate(A[:H - 60].astype(np.float32), tpl, cv2.TM_SQDIFF) / (ctx * (x1 - x0) * 3)
    res[:, np.abs(np.arange(res.shape[1]) - x0) > dx] = np.inf
    res[np.arange(res.shape[0]) + ctx + K > H] = np.inf
    # grass fraction of every K x (px1-px0) window, via an integral image; window top-left = (i + ctx, j + off)
    r_, g_, b_ = A[..., 0], A[..., 1], A[..., 2]
    obj = brown(A) | cream(A) | ((b_ - g_ > 6) & (b_ > 150)) | ((r_ - g_ > 12) & (r_ > 120))
    g = (~obj).astype(np.float64)                     # "grass" here = anything that is not an object to duplicate
    ii = np.zeros((H + 1, W + 1)); ii[1:, 1:] = g.cumsum(0).cumsum(1)
    wpx, off = px1 - px0, px0 - x0
    ny, nx = res.shape
    I = np.arange(ny)[:, None] + ctx; J = np.arange(nx)[None] + off
    valid = (J >= 0) & (J + wpx <= W) & (I + K <= H)
    I2 = np.clip(I, 0, H - K); J2 = np.clip(J, 0, W - wpx)
    gf = (ii[I2 + K, J2 + wpx] - ii[I2, J2 + wpx] - ii[I2 + K, J2] + ii[I2, J2]) / (K * wpx)
    score = np.where(valid, np.sqrt(res) + 300 * (1 - gf), np.inf)
    i, j = np.unravel_index(np.argmin(score), score.shape)
    best = (score[i, j], j, i + ctx, float(np.sqrt(res[i, j])), gf[i, j])
    return best[1], best[2], best[3]


def vcut_join(p1, p2, xlo, xhi, K):
    """Join two full-width patches on a min-error vertical cut in [xlo, xhi]: p1 left of it, p2 right."""
    d = np.abs(p1 - p2).mean(-1)[:, xlo:xhi]
    xs = seam_dp(d, np.zeros(K), np.full(K, xhi - xlo - 1)) + xlo
    out = p1.copy()
    for y in range(K):
        out[y, xs[y]:] = p2[y, xs[y]:]
    return out


def build_left(A, Cb, K=34):
    # bushes (template x 81..205): A's own light-green bushes higher up
    sx, sy, f1 = find_continuation(A, 81, 205, K, ctx=6, dx=60, dymin=60, dymax=1600)
    pb, _ = shifted(A, sx, sy, 81, K)
    # grass verge (template x 262..386): grass-only source
    gx, gy, f2 = find_grass_continuation(A, 262, 386, K, px0=196, px1=380)
    pg, _ = shifted(A, gx, gy, 262, K)
    # path edge (template x 366..404): A's own soft grass/path fringe higher up
    ex, ey, f3 = find_continuation(A, 366, 404, K, ctx=6, dx=70, dymin=35, dymax=500)
    pe, _ = shifted(A, ex, ey, 366, K)
    patch = vcut_join(pb, pg, 192, 212, K)
    patch = vcut_join(patch, pe, 366, 382, K)
    region = np.zeros((K, W), bool); region[:, 81:404] = True
    region[:, 74:81] = True                                   # edge columns left of the phone frame
    # bottom: B's canopy resumes along its own leaf outlines (cut prefers strong edges in B), through cream on the path
    base = Cb[:K]
    gB = np.hypot(*np.gradient(gaussian_filter(lum(base), 0.7)))
    cost = 0.25 * np.abs(patch - base).mean(-1) + 40 * np.exp(-gB / 12.0)
    cols = np.arange(74, 404)
    # bush side (x < 236, light leaves on light leaves): plain min-error cut through flat spots
    grad = np.hypot(*np.gradient(lum(base)))
    cost[:, :236] = (np.abs(patch - base).mean(-1) + 1.0 * grad)[:, :236]
    lo = np.where(cols >= 338, 22, 12)                          # below the object cut by B's top edge at x ~350..372
    cost[:, 338:404] = np.abs(patch - base).mean(-1)[:, 338:404]  # on the path: plain min-error cut
    rows = seam_dp(cost[:, 74:404].T, lo, np.full(len(cols), K - 3), step=2)
    m = region.copy()
    for i, x in enumerate(cols):
        m[rows[i]:, x] = False
    return patch, m, dict(bush=(sx - 81, sy - H, f1), grass=(gx - 262, gy - H, f2), edge=(ex - 366, ey - H, f3))


# ----------------------------------------------------------------------------------------------------------------
# boulder: A's boulder body closes just below the seam (its rock reaches A's last row at x ~216..230 and tapers);
# the closing arc takes texture from the boulder's upper half (translated, then mean/contrast-matched to its lowest
# rows by the edge match), and a soft contact shadow sits under the whole boulder.

def build_boulder(A, Cb, cx=223.0, hw0=7.0, depth=4.0, src=(-40, -80)):
    K = 12
    yy, xx = np.mgrid[0:K, 0:W].astype(float)
    # ellipse arc continuing the body's sides: half-width hw0 at row -1, closing at row `depth`
    t = np.clip((yy + 1) / (depth + 1), 0, 1)
    hw = hw0 * np.sqrt(np.clip(1 - t ** 2, 0, 1))
    cap = (np.abs(xx - cx) <= hw) & (yy <= depth)
    patch = np.zeros((K, W, 3))
    sx, sy = src
    patch[:, :] = A[H + sy:H + sy + K][:, np.clip(np.arange(W) + sx, 0, W - 1)]
    # lower-rim shading: the body's own darkening toward its outline, as a function of distance to the arc
    d = np.clip((hw - np.abs(xx - cx)), 0, None)
    rim = np.clip(1 - d / 3.0, 0, 1) * cap
    patch = patch * (1 - 0.12 * rim[..., None])
    # contact shadow under the boulder (body + lobe, x ~205..262), soft, on whatever B shows there
    e = ((xx - 228) / 22.0) ** 2 + ((yy - 0.5) / 4.0) ** 2
    sh = np.clip(1.1 - e, 0, 1) ** 1.5 * 0.09
    sh[cap] = 0
    shade = Cb[:K] * (1 - sh[..., None])
    return patch, cap, shade, sh


# ----------------------------------------------------------------------------------------------------------------
# seam row: per-column residual against A's last row. The low-frequency part (sigma 3 px across) is matched fully
# and decays over ~4 rows; the high-frequency remainder (soft-clipped at |dL| 10) gets a 3-row feather (0.7, 0.4, 0.15).

def seam_feather(C, sigma=3.0, tau=4.0, hf=(0.7, 0.4, 0.15)):
    r = C[PAD - 1] - C[PAD]
    rl = np.stack([gaussian_filter1d(r[:, c], sigma, mode='nearest') for c in range(3)], -1)
    rh = r - rl
    # large high-frequency residuals are object edges (e.g. a stone rim one px off): feathering them in full would
    # drag A's edge down as a drip, so they are soft-clipped
    mag = np.abs(lum(rh))[:, None]
    rh = rh * np.minimum(1.0, 10.0 / np.maximum(mag, 1e-6))
    out = C.copy()
    alpha = np.zeros(C.shape[:2])
    for k in range(14):
        wl = np.exp(-k / tau)
        wh = hf[k] if k < len(hf) else 0.0
        out[PAD + k] = C[PAD + k] + wl * rl + wh * rh
        alpha[PAD + k] = wh
    return out, alpha


# ----------------------------------------------------------------------------------------------------------------
# B's bushes sitting on the new verge: their outline pixels were anti-aliased against path cream, so the cream share
# of each outline pixel is swapped for the local verge colour; then a soft contact shadow (darker, cooler green, as
# under the artist's own bushes) on the verge just below/beside each bush.

def bush_on_verge(C, bush, verge, cream_rgb=(253.0, 236.0, 206.0)):
    cr = np.array(cream_rgb)
    inner = binary_erosion(bush, iterations=2)
    ring = bush & ~inner & binary_dilation(verge, iterations=2)
    def lmean(mask, s=3.0):
        w = gaussian_filter(mask.astype(float), s)
        return np.stack([gaussian_filter(C[..., c] * mask, s) for c in range(3)], -1) / np.maximum(w, 1e-6)[..., None]
    bc = lmean(inner, 3.0); gc = lmean(verge & ~bush, 3.0)
    d = cr - bc
    f = np.clip(((C - bc) * d).sum(-1) / np.maximum((d * d).sum(-1), 1e-6), 0, 1) * ring
    out = C + f[..., None] * (gc - cr)
    # contact shadow: distance to the bush shifted 2 px down, on verge pixels only
    sh_src = np.zeros_like(bush); sh_src[2:] = bush[:-2]
    dist = distance_transform_edt(~(sh_src | bush))
    w = np.exp(-dist / 2.5) * (verge & ~bush) * (dist < 9)
    tint = np.array([0.80, 0.87, 0.90])
    out = out * (1 - w[..., None] * (1 - tint[None, None]))
    alpha = np.maximum(f, np.clip(w * 2, 0, 1))
    return out, alpha


# ----------------------------------------------------------------------------------------------------------------

def to_canvas(img_b):
    """B-coords array (rows >= 0) -> canvas-coords array (PAD zero rows on top, NB rows)."""
    out = np.zeros((PAD + NB,) + img_b.shape[1:], img_b.dtype)
    n = min(NB, img_b.shape[0])
    out[PAD:PAD + n] = img_b[:n]
    return out


def dbg(C, name, x0=0, x1=W, rows=(PAD - 40, PAD + 300), s=2):
    if not DBG:
        return
    im = Image.fromarray(np.clip(np.round(C[rows[0]:rows[1], x0:x1]), 0, 255).astype(np.uint8))
    im.resize((im.width * s, im.height * s), Image.NEAREST).save(os.path.join(DBG, name))


def main():
    A = load(os.path.join(ROOT, 'A.png'))
    Bw = load(os.path.join(SEAM, 'base', 'B_warp.png'))
    C = np.vstack([A[H - PAD:], Bw[:NB]])
    masks = {}

    comp, reg, info = build_bank(A, Bw)
    m, cut_rows, vcut, bush = bank_mask(comp, reg, info, Bw)
    print('bank chunks', info['chunks'], 'fit %.2f' % info['fit'])
    # the bank/verge is matched and feathered as if B's bushes were not cut out of it; the bushes are then laid back
    # on top with a sub-pixel edge (they are objects in front of the verge, not a seam)
    C0 = C.copy()
    C, al = composite(C, to_canvas(comp), to_canvas(m | bush), r=2.5)
    ba = to_canvas(feather(bush, 0.6))
    C = C * (1 - ba[..., None]) + C0 * ba[..., None]
    masks['bank'] = al * (1 - ba)
    C, ab = bush_on_verge(C, to_canvas(bush), to_canvas(m))
    masks['bushedge'] = ab
    dbg(C, 'bank.png', 520, 860, (0, PAD + 260), 2)

    Cb = C[PAD:]
    patch, m, pinfo = build_pine(A, Cb)
    print('pine src', pinfo['sx'], pinfo['sy'] - H, 'fit %.1f' % pinfo['fit'])
    # the borrowed tier is lighter than A's lowest tier body: the edge match reaches 22 px down (to the tips) so the
    # body keeps A's darkness instead of lightening in a band right under the seam
    C, al = composite(C, to_canvas(patch), to_canvas(m), r=2.5, reach=22.0)
    masks['pine'] = al
    dbg(C, 'pine.png', 680, 937, (0, PAD + 120), 3)

    patch, m, sinfo = build_stone(A, C[PAD:])
    print('stone src', sinfo['sx'] - 530, sinfo['sy'] - H, 'seam dL %.1f' % sinfo['fit'])
    C, al = composite(C, to_canvas(patch), to_canvas(m), r=2.5)
    masks['stone'] = al
    dbg(C, 'stone.png', 480, 680, (10, PAD + 40), 4)

    patch, m, linfo = build_left(A, C[PAD:])
    print('left', linfo)
    C, al = composite(C, to_canvas(patch), to_canvas(m), r=2.0)
    masks['left'] = al

    patch, cap, shade, sh = build_boulder(A, C[PAD:])
    K = cap.shape[0]
    # contact shadow first (multiplicative, soft by construction), then the closing arc
    C[PAD:PAD + K] = shade
    C, al = composite(C, to_canvas(patch), to_canvas(cap), r=1.0, reach=4.0)
    masks['boulder'] = np.maximum(al, to_canvas(np.clip(sh / 0.1, 0, 1)))
    dbg(C, 'left.png', 60, 440, (0, PAD + 80), 3)

    C, al = seam_feather(C)
    masks['seam'] = al
    dbg(C, 'final_right.png', 520, 900, (0, PAD + 230), 2)
    dbg(C, 'final_left.png', 60, 520, (0, PAD + 120), 2)

    out = Bw.copy()
    out[:NB] = C[PAD:]
    # round 2 works only on x >= 401: columns left of that stay byte-identical to vb_join/B_seam.png (the x < 395
    # half is being reworked separately and composited at x = 395)
    XKEEP = 401
    out = np.round(np.clip(out, 0, 255))
    out[:, :XKEEP] = load(os.path.join(SEAM, 'vb_join', 'B_seam.png'))[:, :XKEEP]
    save(out, os.path.join(HERE, 'B_seam.png'))
    full = {}
    for k, a in masks.items():
        f = np.zeros((H, W), np.float32); f[:NB] = a[PAD:]
        full[k] = f
    np.savez(os.path.join(HERE, 'edits.npz'), **full)


if __name__ == '__main__':
    main()
