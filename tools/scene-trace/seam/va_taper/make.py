"""Variant "taper": rebuild B_seam.png and edits.npz from ../../A.png and ../base/B_warp.png.

usage: make.py            (run from anywhere; writes next to this file)

Every edit is a transplant of the art's own pixels (A or warped B) by translation / small scale / custom resample,
colour-matched (per-channel mean and contrast) on a ring around its own boundary, cut along a minimum-error contour
inside an allowed band, and blended with a short feather. Edits, in compositing order:
  path     B's path recoloured to A's path tone near the join (B's own pixels, colour shift fading over 150 rows)
  pine     A's right pine continued downwards (A's lower pine translated down, seam-matched offset)
  grass    A's verge / grass cloned into the triangle between the tapering bank, the path and the pine
  bank     A's right bank strip, straightened, resampled to a width that tapers 74 -> 0 px, laid along the path edge
  bushes   leafy clumps cloned from warped B's right bushes over the pine base and the bank tip
  left     A's bottom-left bushes / grass continued downwards
  boulder  A's boulder lower arc (texture from its own upper part, translated), contact shadow
"""
import os
import numpy as np
import cv2
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter, gaussian_filter1d, binary_closing, binary_opening, label

HERE = os.path.dirname(os.path.abspath(__file__))
SEAM = os.path.dirname(HERE)
W, H = 937, 1678
N = 500                    # editable rows of B
CTX = 300                  # rows of A kept above the join in the working canvas
LUM = np.array([0.299, 0.587, 0.114], np.float32)


def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float32)


A = load(os.path.join(os.path.dirname(SEAM), 'A.png'))
BW = load(os.path.join(SEAM, 'base', 'B_warp.png'))
assert A.shape == (H, W, 3) and BW.shape == (H, W, 3)


class Canvas:
    """Rows -CTX..N-1 in B coordinates (negative = A, read-only)."""

    def __init__(self):
        self.img = np.vstack([A[H - CTX:], BW[:N]]).copy()
        self.edits = {}

    def b(self):
        return self.img[CTX:]

    def L(self):
        return self.img @ LUM


CV = Canvas()
YY, XX = np.mgrid[-CTX:N, 0:W].astype(np.float32)          # canvas pixel coordinates in B coordinates


# ----------------------------------------------------------------------------------------------- source sampling
def sample(src, sx, sy, src_is_A_rows=True):
    """Bicubic sample of a full source image at float coordinates (sx, sy) given in that image's own pixel grid."""
    return cv2.remap(src, sx.astype(np.float32), sy.astype(np.float32), cv2.INTER_CUBIC,
                     borderMode=cv2.BORDER_REFLECT).astype(np.float32)


def translate(src, ox, oy, scale=1.0, rot=0.0, pivot=(0.0, 0.0)):
    """Patch over the canvas: canvas (x, y) shows src at pivot_src + R(rot) * scale * ((x, y) - pivot), where
    pivot_src = pivot + (ox, oy). y in B coordinates; for src = A, B row y continues A row H + y."""
    px, py = pivot
    c, s = np.cos(np.radians(rot)), np.sin(np.radians(rot))
    dx, dy = XX - px, YY - py
    sx = px + ox + scale * (c * dx - s * dy)
    sy = py + oy + scale * (s * dx + c * dy)
    return sample(src, sx, sy)


# ----------------------------------------------------------------------------------------------- masks and cuts
def soft(mask, f):
    """Feathered alpha from a binary mask: 0.5 on the mask boundary, linear over f px."""
    if f <= 0:
        return mask.astype(np.float32)
    mask = mask.copy()
    mask[:CTX] = mask[CTX][None, :]            # the join is not an edit edge: extend the mask upwards into A
    din = distance_transform_edt(mask)
    dout = distance_transform_edt(~mask)
    sd = np.where(mask, din - 0.5, -(dout - 0.5))
    return np.clip(0.5 + sd / f, 0, 1).astype(np.float32)


def cost_map(patch, base):
    Lp, Lb = patch @ LUM, base @ LUM
    d = np.abs(patch - base).mean(2)
    gp = np.hypot(*np.gradient(Lp)); gb = np.hypot(*np.gradient(Lb))
    return d + 0.6 * (gp + gb)


def polar_cut(cost, core, allow, center, nth=900, lam=0.4, step=14):
    """Closed contour r(theta) around `center` (B coords; may lie above the join) that contains `core`, stays inside
    `allow`, and minimises the summed cost along it (DP over theta). Canvas rows < 0 (A) cost nothing.
    cost/core/allow are canvas-sized (CTX + N rows). Returns the binary mask (canvas-sized)."""
    cx, cy = center
    rmax = int(np.hypot(max(cx, W - cx), N - cy + CTX)) + 2
    th = np.linspace(-np.pi / 2, 1.5 * np.pi, nth, endpoint=False)
    rs = np.arange(rmax, dtype=np.float32)
    X = cx + rs[None, :] * np.cos(th)[:, None]
    Y = cy + rs[None, :] * np.sin(th)[:, None]
    inB = (X >= 0) & (X <= W - 1) & (Y >= 0) & (Y <= N - 1)
    inA = (X >= 0) & (X <= W - 1) & (Y < 0) & (Y >= -CTX)
    xi = np.clip(np.round(X).astype(int), 0, W - 1)
    yi = np.clip(np.round(Y).astype(int) + CTX, 0, CTX + N - 1)
    C = np.where(inB, cost[yi, xi], 0.0)
    co = core[yi, xi] & (inB | inA)
    al = (allow[yi, xi] | core[yi, xi]) & inB | inA | ~(inB | inA)
    # must be beyond the last core sample, before the first disallowed sample after it
    last_core = np.where(co.any(1), rmax - 1 - np.argmax(co[:, ::-1], 1), 0)
    big = np.full_like(C, 1e6)
    ok = np.zeros_like(co)
    for i in range(nth):
        lo = last_core[i] + 1 if co[i].any() else 0
        bad = np.flatnonzero(~al[i, lo:])
        hi = lo + (bad[0] if bad.size else rmax - lo)
        ok[i, lo:hi] = True
    C = np.where(ok, C, big)
    acc = C[0].copy()
    back = np.zeros((nth, rmax), np.int16)
    for i in range(1, nth):
        best = np.full(rmax, np.inf); arg = np.zeros(rmax, np.int16)
        for s in range(-step, step + 1):
            sh = np.full(rmax, np.inf)
            if s > 0:
                sh[s:] = acc[:-s]
            elif s < 0:
                sh[:s] = acc[-s:]
            else:
                sh = acc
            v = sh + lam * abs(s)
            m = v < best
            best[m] = v[m]; arg[m] = s
        acc = best + C[i]
        back[i] = arg
    r = np.zeros(nth, int)
    r[-1] = int(np.argmin(acc))
    for i in range(nth - 1, 0, -1):
        r[i - 1] = r[i] - back[i, r[i]]
    # rasterise: inside where pixel radius < contour radius at its angle
    ang = np.arctan2(YY - cy, XX - cx)
    ang = np.where(ang < -np.pi / 2, ang + 2 * np.pi, ang)
    rr = np.hypot(XX - cx, YY - cy)
    rc = np.interp(ang, np.r_[th, th[0] + 2 * np.pi], np.r_[r, r[0]].astype(np.float32))
    return (((rr < rc) & (allow | core)) | core) & (YY >= 0)


def ring(mask, w):
    din = distance_transform_edt(mask); dout = distance_transform_edt(~mask)
    return (din <= w) & mask, (dout <= w) & ~mask


def match(patch, ref_pix, src_pix, gain_lim=(0.8, 1.25), weights=None):
    """Per-channel mean/contrast match: patch' = (patch - mean_src) * g + mean_ref."""
    out = patch.copy()
    for c in range(3):
        a, b = ref_pix[:, c], src_pix[:, c]
        g = np.clip((a.std() + 1e-3) / (b.std() + 1e-3), *gain_lim)
        out[..., c] = (patch[..., c] - b.mean()) * g + a.mean()
    return out


def apply(name, patch, alpha):
    """Composite patch with alpha (canvas-sized) onto B rows only; record alpha."""
    a = alpha.copy(); a[:CTX] = 0
    CV.img = CV.img * (1 - a[..., None]) + patch * a[..., None]
    prev = CV.edits.get(name)
    CV.edits[name] = a[CTX:] if prev is None else np.maximum(prev, a[CTX:])


def seam_fix(patch, sigma=4.0, decay=8.0):
    """Local-mean match along the join: the low-frequency (sigma px along x) difference between A's last row and
    the patch's first row, applied to the patch with an exponential fade over `decay` rows (texture untouched)."""
    p = patch.copy()
    d = A[H - 1] - patch[CTX]
    d = np.stack([gaussian_filter1d(d[:, c], sigma, mode='nearest') for c in range(3)], 1)
    yy = np.arange(N, dtype=np.float32)
    p[CTX:] += np.exp(-yy / decay)[:, None, None] * d[None]
    return p


def seamless(name, patch, core, allow, center, feather=4, match_ref=None, passes=2, lam=0.4, gain_lim=(0.8, 1.25),
             cost_add=None, ring_match=False, seam=False, seam_decay=8.0):
    """Colour-match, min-error cut, feather, composite. match_ref = (canvas_mask_ref, canvas_mask_src) for the
    initial match (ref pixels from the canvas, src pixels from the patch); later passes match on the cut's ring."""
    p = patch
    if match_ref is not None:
        rm, sm = match_ref
        p = match(patch, CV.img[rm], patch[sm], gain_lim)
    if seam:
        p = seam_fix(p, decay=seam_decay)
    mask = None
    for k in range(passes):
        cost = cost_map(p, CV.img)
        if cost_add is not None:
            cost = cost + cost_add
        mask = polar_cut(cost, core, allow, center, lam=lam)
        rin, rout = ring(mask, 4)
        both = (rin | rout) & (YY >= -6)
        w = np.abs((p - CV.img) @ LUM) < 12            # same-material pixels on the ring
        sel = both & w
        if ring_match and sel.sum() > 50 and k < passes - 1:
            p = match(p, CV.img[sel], p[sel], gain_lim)
    alpha = soft(mask, feather)
    alpha[:CTX] = 0
    apply(name, p, alpha)
    return mask, p


def save():
    out = np.vstack([CV.img[CTX:], BW[N:]])
    out = np.clip(np.round(out), 0, 255).astype(np.uint8)
    assert np.array_equal(out[N:], np.clip(np.round(BW[N:]), 0, 255).astype(np.uint8))
    Image.fromarray(out).save(os.path.join(HERE, 'B_seam.png'))
    full = {}
    for k, a in CV.edits.items():
        f = np.zeros((H, W), np.float32); f[:N] = a; full[k] = f
    np.savez(os.path.join(HERE, 'edits.npz'), **full)


# ----------------------------------------------------------------------------------------------- scene geometry
def cream(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    return (r > 215) & (g > 195) & (b > 160) & (r - b < 70) & (r >= g)


def brown(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    return (r - g > 22) & (r < 225) & (r - b > 45)


def a_bank_edges():
    """A's right bank inner/outer edge per A row (H-400..H-1), smoothed."""
    bm = brown(A)
    ys = np.arange(H - 400, H)
    inn, out = [], []
    for y in ys:
        row = bm[y, 540:820]
        row = binary_closing(row, np.ones(7))
        idx = np.flatnonzero(np.diff(np.r_[0, row.astype(int), 0]))
        rs = [(a + 540, b + 540) for a, b in zip(idx[::2], idx[1::2]) if b - a > 30]
        a, b = max(rs, key=lambda r: r[1] - r[0])
        inn.append(a); out.append(b)
    inn = gaussian_filter1d(np.array(inn, float), 2, mode='nearest')
    out = gaussian_filter1d(np.array(out, float), 2, mode='nearest')
    return ys, inn, out


# ================================================================================================ edits
def edit_path():
    """B's path is ~4 levels lighter / pinker than A's: shift B's own path pixels to A's path tone, fading out."""
    ca = cream(A[H - 80:]); cb = cream(BW[:80])
    xs = np.arange(W)
    sel_a = ca & (xs > 410) & (xs < 640); sel_b = cb & (xs > 410) & (xs < 640)
    ma = A[H - 80:][sel_a].mean(0); mb = BW[:80][sel_b].mean(0)
    sa = A[H - 80:][sel_a].std(0); sb = BW[:80][sel_b].std(0)
    print('path tone A', ma.round(1), 'B', mb.round(1))
    p = CV.img.copy()
    p = (p - mb) * np.clip(sa / sb, 1, 1.4) * 0 + (p - mb) + ma       # mean shift only (keep B's own texture)
    cb_full = np.zeros((CTX + N, W), bool); cb_full[CTX:] = cream(BW[:N])
    cb_full = binary_opening(binary_closing(cb_full, np.ones((15, 15))), np.ones((3, 3)))
    lab, _ = label(cb_full)                                                # the path only (not cream mushroom spots)
    keep = np.unique(lab[CTX, 400:650]); keep = keep[keep > 0]
    cb_full = np.isin(lab, keep)
    cb_full[:CTX] = cb_full[CTX][None, :]                                  # the join is not a mask edge
    path = distance_transform_edt(cb_full)
    a_in = np.clip((path - 2) / 6, 0, 1)                                   # 0.5 contour 5 px inside the cream
    t = np.clip(YY / 150, 0, 1)
    fade = 1 - (3 * t * t - 2 * t ** 3)
    alpha = (a_in * fade).astype(np.float32)
    alpha[:CTX] = 0
    apply('path', p, alpha)


def seam_offset(src, x0, x1, oys, oxs, rows=3, weight_rows=None):
    """(ox, oy) such that src rows oy-1-j (shifted by ox) best match A rows H-1-j over x0..x1: B row 0 then continues
    A's last row the way src row oy continues src row oy-1."""
    LA = A @ LUM; LS = src @ LUM
    best = (np.inf, 0, 0)
    for oy in oys:
        for ox in oxs:
            if x0 + ox < 0 or x1 + ox > W:
                continue
            e = np.mean([np.abs(LA[H - 1 - j, x0:x1] - LS[oy - 1 - j, x0 + ox:x1 + ox]).mean() for j in range(rows)])
            if e < best[0]:
                best = (e, ox, oy)
    return best


def box(x0, x1, y0, y1):
    m = (XX >= x0) & (XX < x1) & (YY >= y0) & (YY < y1)
    return m


def flowers(img):
    """Recognisable flower / blossom pixels (purple, white, yellow petals) that must not be duplicated."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    purple = (b > g + 25) & (r > g + 10)
    white = (r > 238) & (g > 238) & (b > 225) & ~cream(img)
    yellow = (r > 225) & (g > 190) & (b < 160) & (r - b > 80)
    m = purple | white | yellow
    return cv2.dilate(m.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0


OVW = 0.04


def quilt(x0, x1, K, src, sx0, sx1, sy0, sy1, tile=40, ov=12, ctx=4, min_shift=40, label='', forbid=None, ovw=None):
    """Seam-continuation band by image quilting: B rows 0..K-1, columns x0..x1 are tiled left to right with blocks
    translated from src[sy0:sy1, sx0:sx1]. Each block is chosen so that the `ctx` src rows above it match A's last
    `ctx` rows (its first row then continues A's last row) and it agrees with the previous block on their overlap;
    neighbouring blocks are joined along a vertical minimum-error cut. Returns a canvas-sized patch (rows < 0 = A)
    and the per-column source offsets."""
    out = CV.img.copy()
    region = src[sy0:sy1, sx0:sx1].astype(np.float32)
    x = x0
    prev_right = None
    shifts = []
    while x < x1:
        tw = min(tile + ov, x1 - x) if prev_right is None else min(tile + ov, x1 - x + 0)
        tmpl = np.zeros((ctx + K, tw, 3), np.float32)
        msk = np.zeros((ctx + K, tw, 3), np.float32)
        tmpl[:ctx] = A[H - ctx:H, x:x + tw]
        msk[:ctx] = 1.0
        if prev_right is not None:
            tmpl[ctx:, :ov] = out[CTX:CTX + K, x:x + ov]
            msk[ctx:, :ov] = OVW if ovw is None else ovw
        res = cv2.matchTemplate(region, tmpl, cv2.TM_SQDIFF, mask=msk)
        # forbid near-copies of what sits directly above the join (doubling)
        ys_, xs_ = np.mgrid[0:res.shape[0], 0:res.shape[1]]
        src_top = sy0 + ys_ + ctx; src_x = sx0 + xs_
        near = (np.abs(src_top - H) < min_shift) & (np.abs(src_x - x) < min_shift)
        res = np.where(near, np.inf, res)
        if forbid is not None:
            fb = forbid[sy0:sy1, sx0:sx1].astype(np.float32)
            ii = cv2.integral(fb)
            hh, ww = res.shape
            y0_, x0_ = ys_ + ctx, xs_
            y1_, x1_ = np.minimum(y0_ + K, fb.shape[0]), np.minimum(x0_ + tw, fb.shape[1])
            cnt = ii[y1_, x1_] - ii[y0_, x1_] - ii[y1_, x0_] + ii[y0_, x0_]
            res = np.where(cnt > 0, np.inf, res)
        iy, ix = np.unravel_index(np.argmin(res), res.shape)
        oy = sy0 + iy + ctx; ox = sx0 + ix - x                 # B row y <- src row oy + y; col x <- x + ox
        blk = src[oy:oy + K, x + ox:x + ox + tw].astype(np.float32)
        if prev_right is None:
            out[CTX:CTX + K, x:x + tw] = blk
        else:
            # vertical min-error cut inside the overlap
            d = np.abs((out[CTX:CTX + K, x:x + ov] - blk[:, :ov]) @ LUM)
            acc = d.copy(); back = np.zeros_like(d, int)
            for r in range(1, K):
                for c in range(ov):
                    lo, hi = max(0, c - 1), min(ov, c + 2)
                    j = lo + int(np.argmin(acc[r - 1, lo:hi]))
                    acc[r, c] += acc[r - 1, j]; back[r, c] = j
            cut = np.zeros(K, int); cut[-1] = int(np.argmin(acc[-1]))
            for r in range(K - 1, 0, -1):
                cut[r - 1] = back[r, cut[r]]
            for r in range(K):
                out[CTX + r, x + cut[r]:x + tw] = blk[r, cut[r]:]
        shifts.append((x, ox, oy - H, float(np.sqrt(res[iy, ix] / max(msk.sum(), 1)))))
        prev_right = True
        x += tile
        if x + ov >= x1:
            break
    if label:
        print(label, 'quilt blocks (x, ox, oy-H, rms):', [(a, b, c, round(d, 1)) for a, b, c, d in shifts])
    return out


def edit_pine():
    """A's right pine continued below the join: quilted from A's own lower pine (seam-matched blocks)."""
    patch = quilt(762, 937, 60, A, 720, 937, H - 450, H - 20, tile=26, ov=10, ctx=3, label='pine', forbid=flowers(A),
                  ovw=0.08)
    core = (box(772, 862, 0, 22) & (XX >= 772 + 0.7 * YY)) | box(862, 937, 0, 10)
    allow = box(762, 937, 0, 55) & (XX >= 763 + 0.7 * YY)          # the skirt's lower-left edge recedes
    # prefer cutting where B's bushes have a lit upper outline (lighter below than above): pine over bush top
    Lb = CV.L()
    lit = np.clip(np.roll(Lb, -3, 0) - np.roll(Lb, 3, 0), 0, 40)
    seamless('pine', patch, core, allow, (870, -60), feather=4, cost_add=0.4 * (40 - lit), seam=True,
             match_ref=(box(770, 937, -8, 0), box(770, 937, 0, 8)))


def edit_verge(bank):
    """A's verge between the bank and the pine (x ~738-765 at the join) continued below the join: A's verge,
    straightened along A's bank outer edge, starting at the A row whose predecessors best match A's last rows."""
    ys_a, outA = bank['ys_a'], bank['outA']
    LA = A @ LUM
    us = np.arange(0, 26)

    def strip(r):
        return LA[r, np.clip((outA[r - ys_a[0]] + us).round().astype(int), 0, W - 1)]
    ref = [strip(H - 1 - j) for j in range(3)]
    best = (np.inf, 0)
    for s0 in range(H - 380, H - 40):
        e = np.mean([np.abs(strip(s0 - 1 - j) - ref[j]).mean() for j in range(3)])
        if e < best[0]:
            best = (e, s0)
    s0 = best[1]
    print(f'verge: source starts at A row {s0 - H} (seam err {best[0]:.2f})')
    o = np.interp(np.clip(YY, 0, N - 1), np.arange(N), bank['out'])
    sy = np.where(YY >= 0, s0 + YY, YY + H)
    sx = np.where(YY >= 0, np.interp(sy, ys_a, outA) + (XX - o), XX)
    patch = sample(A, sx, sy)
    fl = np.zeros((CTX + N, W), bool); fl[CTX:] = flowers(CV.img[CTX:])             # B's yellow flower remnants
    core = ((XX >= o + 3) & (XX <= o + 24) & (YY >= 0) & (YY < 18)) | (fl & (XX < 800) & (YY < 40) & (XX > o))
    allow = (XX >= o - 4) & (XX <= o + 34) & (YY >= 0) & (YY < 40) | (box(740, 812, 0, 44) & (XX > o))
    seamless('grass', patch, core, allow, (752, -20), feather=4, seam=True, seam_decay=22.0)


def edit_grass(bank):
    """Grass between the tapering bank, the path and B's bushes: A's right verge, straightened along A's bank outer
    edge (A rows -115..0) and laid out from the new bank's outer edge."""
    o = np.interp(np.clip(YY, 0, N - 1), np.arange(N), bank['out'])
    sy = np.clip(H - 115 + YY, 0, H - 1)
    outA = np.interp(sy, bank['ys_a'], bank['outA'])
    sx = outA + 3 + (XX - o)
    patch = sample(A, sx, sy)
    cb = np.zeros((CTX + N, W), bool); cb[CTX:] = cream(CV.img[CTX:])
    cb = cv2.dilate(cb.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    core = cb & (XX >= o - 4) & (YY >= 0) & (YY < 112) & (XX > 670) & (XX < o + 36)     # not the mushroom's spots
    allow = (XX >= o - 14) & (XX < o + 40) & (YY >= 20) & (YY < 122)
    seamless('grass', patch, core, allow, (720, 50), feather=4)


def bank_geometry():
    ys_a, inA, outA = a_bank_edges()
    sl_in = (inA[-1] - inA[-21]) / 20
    sl_out = (outA[-1] - outA[-21]) / 20
    w0 = outA[-1] - inA[-1]
    y = np.arange(N, dtype=float)
    Y1 = 128.0                                          # width reaches 0 here (hidden under the bushes)
    t = np.clip(y / Y1, 0, 1)
    inn = inA[-1] + sl_in * y - 0.00012 * y * y
    w = w0 * np.cos(np.pi / 2 * t) ** 1.0 + (sl_out - sl_in) * y * (1 - t) ** 2
    w = np.clip(w, 0, None)
    return dict(ys_a=ys_a, inA=inA, outA=outA, w0=w0, Y1=Y1, **{'in': inn, 'out': inn + w, 'w': w})


def edit_bank(g):
    """A's bank, straightened along its own inner edge, resampled to the tapering width (inner rim and the dark
    scalloped outer rim keep their own width; the pebbly interior is compressed), laid along the path edge."""
    ys_a, inA, outA = g['ys_a'], g['inA'], g['outA']
    w0, w = g['w0'], g['w']
    # source row advance per B row: interior compression ratio, floored
    ratio = np.clip((w - 14) / (w0 - 14), 0, 1)
    step = np.maximum(0.3, ratio)
    # seam-continuity: pick the starting source row whose predecessor rows look like A's last rows (straightened)
    LA = A @ LUM
    us = np.arange(-8, int(w0) + 10)

    def strip(s):
        return LA[int(s), np.clip((inA[int(s) - ys_a[0]] + us).round().astype(int), 0, W - 1)]
    ref = [strip(H - 1 - j) for j in range(3)]
    best = (np.inf, 0)
    for s0 in range(H - 300, H - 60):
        e = np.mean([np.abs(strip(s0 - 1 - j) - ref[j]).mean() for j in range(3)])
        if e < best[0]:
            best = (e, s0)
    s0 = best[1]
    print(f'bank: source starts at A row {s0 - H} (seam err {best[0]:.2f}), w0 {w0:.1f}')
    s = s0 + np.r_[0, np.cumsum(step[:-1])]
    # per canvas pixel source coordinates
    yb = np.clip(YY, 0, N - 1).astype(int)
    sy = np.where(YY >= 0, s[yb], YY + H)                       # above the join: identity (A itself)
    i_in = np.interp(sy, ys_a, inA); i_out = np.interp(sy, ys_a, outA)
    b_in = np.where(YY >= 0, g['in'][yb], i_in); b_out = np.where(YY >= 0, g['out'][yb], i_out)
    x = XX
    inner = i_in + (x - b_in)
    outer = i_out + (x - b_out)
    lo, hi = b_in + 6, b_out - 8
    span = np.maximum(hi - lo, 1e-3)
    mid = i_in + 6 + (x - lo) / span * ((i_out - 8) - (i_in + 6))
    narrow = (hi - lo) < 1
    sx = np.where(x <= lo, inner, np.where(x >= hi, outer, mid))
    sx = np.where(narrow, np.where(x < (b_in + b_out) / 2, inner, outer), sx)
    patch = sample(A, sx, sy)
    core = (XX >= b_in - 2) & (XX <= b_out + 2) & (YY >= 0) & (YY < 112) & (np.interp(YY, np.arange(N), w) > 9)
    allow = (XX >= b_in - 14) & (XX <= b_out + 16 + 10 * np.clip(1 - YY / 30, 0, 1)) & (YY >= 0) & (YY < 140)
    mask, p = seamless('bank', patch, core, allow, (700, -90), feather=3,
                       match_ref=(box(640, 760, -16, 0), box(640, 760, -16, 0)), gain_lim=(0.9, 1.1), seam=True)
    return p


def ellipse(cx, cy, rx, ry):
    return ((XX - cx) / rx) ** 2 + ((YY - cy) / ry) ** 2 <= 1


def edit_bushes():
    """Hide the bank's tip under a leafy clump cloned from warped B's own right-side bush (the dark clump at
    x 690-790, y 55-115, whose lobed left outline sits against the path), scaled 0.9 and moved 45 px left / 23 px
    down so it overhangs the island's top-left corner and the tip."""
    pivot = (690.0, 108.0)
    patch = translate(BW, 45, -23, scale=0.9, rot=-4, pivot=pivot)
    core = ellipse(668, 110, 20, 15)
    allow = ellipse(684, 106, 54, 34) & (YY >= 0)
    seamless('bushes', patch, core, allow, (676, 108), feather=3, lam=2.0)


def edit_boulder():
    """A's boulder: its dark underside (x ~214-230) is cut by the join. Close it with a lower arc built from the
    boulder's own pixels just above the join (A rows -4..-1, translated down and resampled towards the arc's centre with an
    elliptical narrowing), then a soft contact shadow on the bushes below."""
    cx, a, b, d0 = 222.0, 9.0, 9.0, 3.0
    hw0 = a * np.sqrt(1 - (d0 / b) ** 2)
    d = np.clip(YY + 1 + d0, 0, b - 1e-3)
    hw = a * np.sqrt(1 - (d / b) ** 2)
    k = hw0 / np.maximum(hw, 0.5)
    sx = np.clip(cx + (XX - cx) * k, cx - 40, cx + 40)
    sy = H - 4 + np.clip(YY, 0, 10) * 0.4
    rock = sample(A, sx, sy)
    inside = (np.abs(XX - cx) <= hw) & (YY >= 0) & (YY + 1 + d0 < b)
    alpha = soft(inside, 2.0) * (YY >= 0)
    # contact shadow: darken what lies just under the arc (feathered ellipse)
    sh = np.clip(1 - np.sqrt(((XX - cx) / 16) ** 2 + ((YY - 6) / 6) ** 2), 0, 1) ** 0.8
    shaded = CV.img * (1 - 0.16 * sh[..., None])
    patch = shaded * (1 - alpha[..., None]) + rock * alpha[..., None]
    a_all = np.clip(np.maximum(alpha, (sh > 0.02) * 1.0), 0, 1).astype(np.float32)
    a_all[:CTX] = 0
    apply('boulder', patch, a_all)


def edit_stone():
    """A's oval path stone (x 545-620) is cut at its lower rim by the join: close the rim in B's first rows by
    resampling A's last row towards the stone's centre with an elliptical narrowing (A's own rim pixels)."""
    cx, a, b, d0 = 583.0, 38.0, 20.0, 14.0           # centre x, semi-axes, depth of A's last row below the centre
    hw0 = a * np.sqrt(1 - (d0 / b) ** 2)
    d = np.clip(YY + 1 + d0, 0, b - 1e-3)
    hw = a * np.sqrt(1 - (d / b) ** 2)
    k = np.where(YY >= 0, hw0 / np.maximum(hw, 0.5), 1.0)
    sx = np.clip(cx + (XX - cx) * k, 538, 628)
    sy = np.full_like(YY, H - 1.0)
    patch = sample(A, sx, sy)
    # below the stone the resample reads A's own cream from the same row; keep it only inside a small box
    core = box(548, 618, 0, 5)
    allow = box(530, 640, 0, 10)
    seamless('stone', patch, core, allow, (583, -10), feather=3, seam=True)


def edit_pathfix():
    """Remove the bits of B's grass lip left on the path at the join (x ~392-430, y 0-12): B's own path cream from
    40 px to the right, translated."""
    patch = translate(CV.img[CTX:].copy() if False else np.vstack([A[H - CTX:], CV.img[CTX:]])[CTX:], 40, 0)
    _, _, elc = left_edge()
    core = box(384, 428, 0, 10) & ~(np.vstack([np.zeros((CTX, W), bool), cream(CV.img[CTX:])])) & (XX > elc + 4)
    allow = box(386, 445, 0, 20)
    seamless('pathfix', patch, core, allow, (412, 0), feather=3)
    # B's pink-grey path shading right under the join beside the bank (A's path has none there): B's own clean
    # path cream from 70 px to the left
    stack = np.vstack([A[H - CTX:], CV.img[CTX:]])[CTX:]
    patch = translate(stack, -70, 0)
    Lc = CV.L()
    core = box(604, 655, 0, 26) & (Lc < 232) & (YY >= 0)
    allow = box(590, 662, 0, 40)
    seamless('pathfix', patch, core, allow, (630, 0), feather=4)


def left_edge():
    """A's path left edge per row (A rows H-140..H-1) and the new left edge in B (canvas-sized): from A's edge at the
    join it curves in under B's canopy outline (x ~340 at y 58), smoothstep."""
    ys = np.arange(H - 140, H)
    cm = cream(A[ys[0]:H])
    xl = []
    for r in cm:
        idx = np.flatnonzero(np.diff(np.r_[0, r[300:700].astype(int), 0]))
        rs = [(a0 + 300, b0 + 300) for a0, b0 in zip(idx[::2], idx[1::2])]
        xl.append(max(rs, key=lambda q: q[1] - q[0])[0])
    xl = gaussian_filter1d(np.array(xl, float), 3, mode='nearest')
    e0 = xl[-1]
    y = np.arange(N, dtype=float)
    t = np.clip(y / 58, 0, 1)
    el = e0 + (340 - e0) * (3 * t * t - 2 * t ** 3)
    return ys, xl, np.interp(np.clip(YY, 0, N - 1), y, el)


def edit_left_verge():
    """A's left verge (grass along the path's left edge), straightened along A's path edge and laid along a smooth
    path edge from A's (x 388 at the join) that curves in under B's canopy outline (x ~340 at y 58), filling the cream
    between the canopy and the new edge."""
    ys, xl, elc = left_edge()
    sy = np.where(YY >= 0, H - 50 + YY * 0.6, YY + H)                   # A rows -50..-14: below the white flower
    xlA = np.interp(sy, ys, xl)
    sx = np.where(YY >= 0, xlA + (XX - elc), XX)
    patch = sample(A, sx, sy)
    cb = np.zeros((CTX + N, W), bool); cb[CTX:] = cream(CV.img[CTX:])
    cb = cv2.dilate(cb.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    core = (cb & (XX >= elc - 52) & (XX <= elc - 4) & (YY >= 0) & (YY < 56)) | \
        (~cb & (XX >= elc + 1) & (XX <= elc + 7) & (YY >= 0) & (YY < 56))          # B's lip remnants on the path
    allow = (XX >= elc - 58) & (XX <= elc + 10) & (YY >= 0) & (YY < 62)              # stops above the lamp arm
    seamless('leftverge', patch, core, allow, (380, 30), feather=4, seam=True)


def edit_left():
    """A's bottom-left bushes and grass continued below the join (quilted from A's own bottom-left, flowers excluded),
    cut into B's canopy along a minimum-error contour."""
    r, g_, b_ = A[..., 0], A[..., 1], A[..., 2]
    rock = (b_ > g_ + 5) & (b_ > 150) & ~cream(A)
    forbid = flowers(A) | (cv2.dilate(rock.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0)
    patch = quilt(0, 396, 50, A, 0, 430, H - 450, H - 20, tile=16, ov=8, ctx=3, label="left", forbid=forbid,
                  ovw=0.08)
    _, _, elc = left_edge()
    core = box(0, 392, 0, 6) & (XX < elc - 2)
    allow = box(0, 400, 0, 50) & (XX < elc - 4 + 12 * np.clip(1 - YY / 8, 0, 1))
    seamless('left', patch, core, allow, (200, -150), feather=4, seam=True)


if __name__ == '__main__':
    edit_path()
    bank = bank_geometry()
    edit_verge(bank)
    edit_pine()
    edit_grass(bank)
    edit_bank(bank)
    edit_bushes()
    edit_left()
    edit_boulder()
    edit_pathfix()
    edit_left_verge()
    edit_stone()
    save()
