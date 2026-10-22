"""Round 2, left side only (x < 389) on top of vb_join/B_seam.png.

usage: make.py            (writes vl_left_r2/B_seam.png and vl_left_r2/edits.npz)

Base: ../vb_join/B_seam.png. Columns >= 389 are copied unchanged (asserted). For x < 389 the left band is rebuilt
from ../base/B_warp.png and A's own pixels as layers, back to front:
  behind   A's bottom band continued downwards: vb_join's seam-matched translations of A (bushes: A shifted by
           dx -35 / A row -217; grass: dx +70 / A row -767), extended to 90 rows so it can show deeper where the
           canopy dips; joined on a vertical min-error cut.
  fringe   A's path-edge grass fringe (rows -50..-14, below A's white flower), straightened along A's left path edge
           and laid along a new edge that leaves A's edge at the join (x 388) and curves in under B's canopy outline
           (x ~342 at y 52). Its edge is A's own tufted edge; its end tucks under B's canopy leaves.
  canopy   B's canopy in front: everything below an irregular boundary c(x) that follows B's own leaf-cluster top
           outlines (a DP over columns rewarding "lighter below" edges in B, steps up to 7 rows/column, with a prior
           that lifts it to clusters near y 6-18 and lets it drop to y ~45-55 between clusters).
  shade    the canopy's soft shadow on what lies behind it: the behind layer darkened up to 18 % within ~9 px above
           the canopy outline (multiplicative, B's own shading style).
  boulder  A's boulder underside (x ~213-232) closed with an elliptic arc resampled from its own last rows
           (A rows -4..-1, sampled only inside the rock), plus a soft contact shadow on the grass.
  seam     the join row matched like vb_join's: low-frequency residual (sigma 3 px) decaying over 4 rows, high-
           frequency residual (soft-clipped at |dL| 10) feathered over 3 rows, applied to x < 389 only.
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter, gaussian_filter1d, map_coordinates

HERE = os.path.dirname(os.path.abspath(__file__))
SEAM = os.path.dirname(HERE)
ROOT = os.path.dirname(SEAM)
W, H = 937, 1678
XC = 389                     # columns >= XC stay identical to vb_join
K = 90                       # rows rebuilt
LUM = np.array([0.299, 0.587, 0.114])


def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float64)


def lum(img):
    return img @ LUM


A = load(os.path.join(ROOT, 'A.png'))
BW = load(os.path.join(SEAM, 'base', 'B_warp.png'))
V = load(os.path.join(SEAM, 'vb_join', 'B_seam.png'))
YY, XX = np.mgrid[0:K, 0:W].astype(float)


def feather(mask, r):
    m = mask.astype(bool)
    sd = distance_transform_edt(m) - distance_transform_edt(~m)
    return np.clip(0.5 + sd / (2.0 * r), 0, 1)


def dp_rows(cost, lo, hi, step, lam, side=None):
    """Horizontal path through cost[y, x] (one row per column), rows in [lo[x], hi[x]], |dy| <= step per column.
    `side[y, x]`: cost per row of a vertical run in column x (so jumps follow vertical outlines)."""
    Hc, Wc = cost.shape
    S = None if side is None else np.vstack([np.zeros((1, Wc)), np.cumsum(side, 0)])
    big = 1e12
    c = np.full((Hc, Wc), big)
    for x in range(Wc):
        c[int(lo[x]):int(hi[x]) + 1, x] = cost[int(lo[x]):int(hi[x]) + 1, x]
    acc = c[:, 0].copy(); back = np.zeros((Hc, Wc), np.int16)
    for x in range(1, Wc):
        best = np.full(Hc, big); arg = np.zeros(Hc, np.int16)
        for s in range(-step, step + 1):
            sh = np.full(Hc, big)
            if s > 0:
                sh[s:] = acc[:-s]
            elif s < 0:
                sh[:s] = acc[-s:]
            else:
                sh = acc.copy()
            sh = sh + lam * abs(s)
            if S is not None and s != 0:
                yy = np.arange(Hc); yp = np.clip(yy - s, 0, Hc - 1)
                sh = sh + np.abs(S[np.maximum(yy, yp), x] - S[np.minimum(yy, yp), x])
            b = sh < best
            best[b] = sh[b]; arg[b] = s
        acc = best + c[:, x]; back[:, x] = arg
    ys = np.zeros(Wc, int); ys[-1] = int(np.argmin(acc))
    for x in range(Wc - 1, 0, -1):
        ys[x - 1] = ys[x] - back[ys[x], x]
    return ys


def dp_cols(cost, lo, hi, step=1):
    """Vertical path (one column per row)."""
    return dp_rows(cost.T, lo, hi, step, 0.15)


def cream(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    return (r > 215) & (g > 195) & (b > 160) & (r - b < 70) & (r >= g)


def shifted(dx, dy):
    """B rows 0..K-1: A translated so B(x, y) = A(x + dx, H + dy + y)."""
    xs = np.clip(np.arange(W) + dx, 0, W - 1)
    return A[H + dy:H + dy + K][:, xs]


# ------------------------------------------------------------------------------------------------ geometry
def a_left_edge():
    """A's path left edge per row (rows H-160..H-1), smoothed."""
    ys = np.arange(H - 160, H)
    cm = cream(A[ys[0]:H])
    xl = []
    for r in cm:
        idx = np.flatnonzero(np.diff(np.r_[0, r[300:700].astype(int), 0]))
        rs = [(a0 + 300, b0 + 300) for a0, b0 in zip(idx[::2], idx[1::2])]
        xl.append(max(rs, key=lambda q: q[1] - q[0])[0])
    return ys, gaussian_filter1d(np.array(xl, float), 3, mode='nearest')


YS_A, XL_A = a_left_edge()
E0 = XL_A[-1]
Y_END = 52.0                 # the fringe edge reaches B's canopy outline here
X_END = 342.0


def new_edge(y):
    t = np.clip(np.asarray(y, float) / Y_END, 0, 1)
    # leaves A's edge with A's own (near-vertical) slope, curves in with a smoothstep
    return E0 + (X_END - E0) * (3 * t * t - 2 * t ** 3)


# ------------------------------------------------------------------------------------------------ layers
def behind_layer():
    pb = shifted(-35, -217)                  # vb_join's bush continuation (x 81..205)
    pg = shifted(70, -767)                   # vb_join's grass continuation (x 262..386)
    d = np.abs(pb - pg).mean(-1)[:, 192:212]
    xs = dp_cols(d, np.zeros(K), np.full(K, 19)) + 192
    out = pb.copy()
    for y in range(K):
        out[y, xs[y]:] = pg[y, xs[y]:]
    return out


def fringe_layer():
    """A's path-edge fringe straightened along A's left edge, laid along new_edge(y). Source rows start at the A row
    whose predecessors best continue A's last rows (straightened), searched below A's white flower (rows > -58)."""
    LA = lum(A)
    us = np.arange(-40, 6)

    def strip(r):
        e = np.interp(r, YS_A, XL_A)
        return LA[r, np.clip(np.round(e + us).astype(int), 0, W - 1)]
    ref = [strip(H - 1 - j) for j in range(3)]
    best = (np.inf, 0)
    for s0 in range(H - 56, H - 20):
        e = np.mean([np.abs(strip(s0 - 1 - j) - ref[j]).mean() for j in range(3)])
        if e < best[0]:
            best = (e, s0)
    s0 = best[1]
    step = 0.55                                         # A rows per B row: (Y_END + 8) rows from ~34 source rows
    sy = s0 + YY * step
    sy = np.minimum(sy, H - 2)
    ex = new_edge(YY)
    sx = np.interp(sy, YS_A, XL_A) + (XX - ex)
    out = np.stack([map_coordinates(A[..., c], [sy, sx], order=3, mode='nearest') for c in range(3)], -1)
    return out, s0 - H, best[0]


def canopy_boundary():
    """c(x): first canopy row per column (x < XC). Follows B's own leaf outlines: rows where B is lighter just below
    than just above (a leaf's lit top edge over the darker leaves behind it)."""
    Lb = gaussian_filter(lum(BW[:K]), 0.8)
    lit = np.zeros_like(Lb)
    lit[3:-3] = Lb[6:] - Lb[:-6]
    cost = 30 * np.exp(-np.clip(lit, 0, None) / 9.0)
    x = np.arange(W)
    # prior: clusters reach up at x ~120-165 and ~255-300, the boulder/grass gap and the far left sit deeper
    knots_x = [0, 60, 90, 112, 150, 175, 195, 215, 235, 255, 280, 300, 330, 350, 389, W - 1]
    knots_y = [30, 40, 38, 6, 5, 8, 22, 30, 48, 20, 6, 12, 20, 30, 45, 45]
    prior = np.interp(x, knots_x, knots_y)
    cost = cost + 0.25 * np.abs(YY - prior[None, :])
    gx = np.zeros_like(Lb); gx[:, 2:-2] = np.abs(Lb[:, 4:] - Lb[:, :-4])
    side = 3.0 * np.exp(-gx / 8.0)
    lo = np.full(W, 3); hi = np.full(W, 62)
    ys = dp_rows(cost[:, :XC], lo[:XC], hi[:XC], step=6, lam=0.3, side=side[:, :XC])
    c = np.full(W, K)
    c[:XC] = ys
    return c, prior


def main():
    Bw = BW[:K]
    beh = behind_layer()
    fr, fr_src, fr_fit = fringe_layer()
    print(f'fringe source starts at A row {fr_src} (fit {fr_fit:.2f})')
    c, prior = canopy_boundary()
    print('canopy boundary rows (x 81..388 every 20):', c[81:XC:20].tolist())

    ex = new_edge(YY)
    canopyB = ~cream(Bw)                                 # B's canopy / lamp pixels (not path cream)
    front = (YY >= c[None, :]) & canopyB
    front &= XX < XC
    # behind region: above the canopy outline, left of the new path edge (fringe takes the last 40 px)
    region = (XX < XC) & ~front & (XX < ex + 6) & (YY < 62)
    # the fringe strip: band [ex - 40, ex + 5], rows < Y_END + 6; joined to `behind` on a vertical min cut
    band = (XX >= ex - 40) & (XX <= ex + 2) & (YY < Y_END + 6) & (XX < XC)
    d = np.abs(fr - beh).mean(-1) + 0.5 * np.hypot(*np.gradient(lum(fr)))
    lo = np.clip(np.round(new_edge(np.arange(K)) - 40), 0, W - 1)
    hi = np.clip(np.round(new_edge(np.arange(K)) - 14), 0, W - 1)
    xs = dp_cols(d, lo, hi, step=2)
    take_fr = np.zeros((K, W), bool)
    for y in range(K):
        take_fr[y, xs[y]:] = True
    take_fr &= band

    lay = beh.copy()
    a_fr = feather(take_fr, 2.0) * band
    lay = lay * (1 - a_fr[..., None]) + fr * a_fr[..., None]

    # canopy shadow on the behind layer: up to 18 % darker within ~9 px above the canopy outline
    dist = distance_transform_edt(~front)
    sh = 0.18 * np.clip(1 - dist / 9.0, 0, 1) ** 1.6
    lay = lay * (1 - sh[..., None])

    # composite: behind/fringe inside region, B elsewhere (canopy, cream right of the new edge, rows below)
    a_reg = feather(region, 1.5) * (XX < XC)
    out = Bw * (1 - a_reg[..., None]) + lay * a_reg[..., None]

    # boulder underside: elliptic closing arc from the rock's own last rows, then contact shadow
    cx, a, b, d0 = 222.0, 9.0, 9.0, 3.0
    hw0 = a * np.sqrt(1 - (d0 / b) ** 2)
    dd = np.clip(YY + 1 + d0, 0, b - 1e-3)
    hw = a * np.sqrt(1 - (dd / b) ** 2)
    k = hw0 / np.maximum(hw, 0.5)
    sx = np.clip(cx + (XX - cx) * k, cx - hw0 + 0.5, cx + hw0 - 0.5)       # sample inside the rock only
    sy = H - 4 + np.clip(YY, 0, 10) * 0.4
    rock = np.stack([map_coordinates(A[..., ch], [sy, sx], order=1, mode='nearest') for ch in range(3)], -1)
    inside = (np.abs(XX - cx) <= hw) & (YY + 1 + d0 < b)
    a_rock = feather(inside, 1.0)
    cshadow = 0.15 * np.clip(1 - np.sqrt(((XX - cx - 2) / 18) ** 2 + ((YY - 4) / 5.5) ** 2), 0, 1) ** 1.2
    cshadow[inside] = 0
    out = out * (1 - cshadow[..., None])
    out = out * (1 - a_rock[..., None]) + rock * a_rock[..., None]

    # seam row (x < XC): vb_join's method
    r = A[H - 1] - out[0]
    rl = np.stack([gaussian_filter1d(r[:, ch], 3.0, mode='nearest') for ch in range(3)], -1)
    rh = r - rl
    mag = np.abs(lum(rh))[:, None]
    rh = rh * np.minimum(1.0, 10.0 / np.maximum(mag, 1e-6))
    a_seam = np.zeros((K, W))
    hf = (0.7, 0.4, 0.15)
    for kk in range(14):
        wl = np.exp(-kk / 4.0)
        wh = hf[kk] if kk < 3 else 0.0
        out[kk, :XC] += wl * rl[:XC] + wh * rh[:XC]
        a_seam[kk, :XC] = wh

    final = V.copy()
    final[:K, :XC] = out[:, :XC]
    res = np.clip(np.round(final), 0, 255).astype(np.uint8)
    assert np.array_equal(res[:, XC:], np.clip(np.round(V), 0, 255).astype(np.uint8)[:, XC:])
    Image.fromarray(res).save(os.path.join(HERE, 'B_seam.png'))

    def full(a):
        f = np.zeros((H, W), np.float32); f[:K] = a; f[:, XC:] = 0
        return f
    np.savez(os.path.join(HERE, 'edits.npz'),
             behind=full(a_reg * (1 - a_fr)), fringe=full(a_reg * a_fr), shade=full((sh > 0.02) * a_reg),
             boulder=full(np.maximum(a_rock, cshadow > 0.01)), seam=full(a_seam))


if __name__ == '__main__':
    main()
