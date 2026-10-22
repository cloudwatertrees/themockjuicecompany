"""Make B_seam.png: B's top band edited so it continues A's bottom row.

usage: seam.py METHOD [--band L] [--out PATH]
  METHOD poisson : path-anchored warp of B, then a gradient-domain (Poisson) blend that pins row -1 to A's last row.
  METHOD cut     : path-anchored warp of B, then A's bottom rows mirrored downward and joined to the warped B along a
                   minimum-error cut (dynamic programming, no alpha blending except a 2 px feather), then a short
                   Poisson pass to remove the residual low-frequency offset.

The warp is horizontal only. Per row k of B (k < L) the anchors are B's own path edges l(k), r(k); they move by
dl * w(k), dr * w(k), with dl, dr the row-0 mismatch to A's last row and w a smoothstep from 1 (k = 0) to 0 (k = L).
Outside the path the displacement is held constant out to x = 81 / 856 (the phone-visible range) and tapers to 0 at the
canvas edges, so compression sits outside the visible range.
"""
import argparse
import numpy as np
from PIL import Image
from scipy.ndimage import binary_closing, gaussian_filter1d, map_coordinates, median_filter
from scipy.sparse import diags, kron, identity, csr_matrix
from scipy.sparse.linalg import factorized

W, H = 937, 1678
VIS = (81, 856)


def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float64)


def cream(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    return (r > 215) & (g > 195) & (b > 160) & (r - b < 70) & (r >= g)


def path_edges(img, rows, near=None):
    """Left/right cream-path edge per row (largest run, or the run overlapping `near`)."""
    m = cream(img)
    out = []
    for y in rows:
        mm = binary_closing(m[y], np.ones(9))
        idx = np.flatnonzero(np.diff(np.r_[0, mm.astype(int), 0]))
        rs = list(zip(idx[::2], idx[1::2]))
        if near is not None and out:
            c = (out[-1][0] + out[-1][1]) / 2
            rs = [r for r in rs if r[0] <= c <= r[1]] or rs
        out.append(max(rs, key=lambda r: r[1] - r[0]))
    return np.array(out, np.float64)


def smoothstep(t):
    t = np.clip(t, 0, 1)
    return 1 - (3 * t * t - 2 * t * t * t)


def warp_B(A, B, L):
    ea = path_edges(A, [H - 1])[0]                      # A's last-row path edges
    eb = path_edges(B, range(L + 1), near=True)
    eb = np.stack([gaussian_filter1d(median_filter(eb[:, i], 9, mode='nearest'), 3, mode='nearest') for i in (0, 1)], 1)
    dl, dr = ea[0] - eb[0, 0], ea[1] - eb[0, 1]
    out = B.copy()
    xs = np.arange(W, dtype=np.float64)
    for k in range(L):
        w = smoothstep(k / L)
        l, r = eb[k]
        tl, tr = l + dl * w, r + dr * w
        # target anchors -> source anchors; displacement constant out to the visible edges, 0 at canvas edges
        tx = [0, VIS[0], tl, tr, VIS[1], W - 1]
        sx = [0, VIS[0] - dl * w, l, r, VIS[1] - dr * w, W - 1]
        src = np.interp(xs, tx, sx)
        for c in range(3):
            out[k, :, c] = map_coordinates(B[k:k + 1, :, c], [np.zeros(W), src], order=3, mode='nearest')
    return np.clip(out, 0, 255), (dl, dr)


def poisson_band(target, top_row, P, seam_step):
    """Re-solve rows 0..P-1 of `target` so their gradients match target's own, row -1 is `top_row` (A's last row) and
    the step from row -1 to row 0 is `seam_step` (A's own last step). Dirichlet at rows -1 and P, Neumann at x edges."""
    ey = diags([-1, 2, -1], [-1, 0, 1], shape=(P, P), dtype=float)
    ex = diags([-1, 2, -1], [-1, 0, 1], shape=(W, W), dtype=float).tolil()
    ex[0, 0] = ex[-1, -1] = 1
    solve = factorized((kron(ey, identity(W)) + kron(identity(P), csr_matrix(ex))).tocsc())
    out = target.copy()
    for c in range(3):
        g = target[:P + 1, :, c]
        b = np.zeros((P, W))
        b[1:] += g[1:P] - g[:P - 1]                     # up neighbours inside the band
        b[0] += seam_step[:, c] + top_row[:, c]         # up neighbour of row 0: guided step + Dirichlet value
        b += g[:P] - g[1:P + 1]                         # down neighbours (row P is Dirichlet)...
        b[-1] += g[P]                                   # ...with its known value
        b[:, 1:] += g[:P, 1:] - g[:P, :-1]
        b[:, :-1] += g[:P, :-1] - g[:P, 1:]
        out[:P, :, c] = solve(b.ravel()).reshape(P, W)
    return np.clip(out, 0, 255)


def mirror_cut(A, Wb, K, kmin):
    """A's bottom K rows mirrored below its last row, joined to Wb along a min-error cut c(x) in [kmin, K)."""
    M = A[H - 2 - np.arange(K)]                           # start one row in: M[0] = A[H-2], so A[H-1] -> M[0] is one step
    lum = np.array([0.299, 0.587, 0.114])
    d = np.abs((M - Wb[:K]) @ lum)
    gm = np.abs(np.diff(M @ lum, axis=0, prepend=(M @ lum)[:1]))
    gw = np.abs(np.diff(Wb[:K] @ lum, axis=0, prepend=(Wb[:K] @ lum)[:1]))
    cost = d + 0.5 * (gm + gw)
    cost[:kmin] = 1e9
    # horizontal-path DP: one cut row per column, |dc| <= 3 per column
    acc = cost[:, 0].copy(); back = np.zeros((K, W), np.int16)
    step = 3
    for x in range(1, W):
        best = np.full(K, np.inf); arg = np.zeros(K, np.int16)
        for s in range(-step, step + 1):
            sh = np.full(K, np.inf)
            if s >= 0:
                sh[s:] = acc[:K - s] if s else acc
            else:
                sh[:s] = acc[-s:]
            pen = sh + 0.6 * abs(s)
            better = pen < best
            best[better] = pen[better]; arg[better] = s
        acc = best + cost[:, x]; back[:, x] = arg
    c = np.zeros(W, int); c[-1] = int(np.argmin(acc))
    for x in range(W - 1, 0, -1):
        c[x - 1] = c[x] - back[c[x], x]
    rows = np.arange(K)[:, None]
    alpha = np.clip((c[None, :] + 1 - rows) / 2.0, 0, 1)[..., None]   # 1 above the cut, 2 px feather
    out = Wb.copy()
    out[:K] = alpha * M + (1 - alpha) * Wb[:K]
    return out, c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('method', choices=['poisson', 'cut'])
    ap.add_argument('--band', type=int, default=260)
    ap.add_argument('--poisson', type=int, default=120)
    ap.add_argument('--K', type=int, default=60)
    ap.add_argument('--kmin', type=int, default=4)
    ap.add_argument('--out', default='B_seam.png')
    a = ap.parse_args()
    A = load('A.png')
    B = load('B_orig.png')[:H]                            # trim the bottom row: 937x1678
    Wb, (dl, dr) = warp_B(A, B, a.band)
    print(f'warp: dl {dl:+.1f} dr {dr:+.1f} over {a.band} rows')
    if a.method == 'poisson':
        out = poisson_band(Wb, A[H - 1], a.poisson, A[H - 1] - A[H - 2])
    else:
        out, c = mirror_cut(A, Wb, a.K, a.kmin)
        print('cut rows: min %d max %d mean %.1f (visible range mean %.1f)' % (c.min(), c.max(), c.mean(), c[VIS[0]:VIS[1]].mean()))
        out = poisson_band(out, A[H - 1], a.poisson, A[H - 1] - A[H - 2])
    Image.fromarray(np.round(out).astype(np.uint8)).save(a.out)
    Image.fromarray(np.round(Wb).astype(np.uint8)).save(a.out.replace('.png', '_warp.png'))


if __name__ == '__main__':
    main()
