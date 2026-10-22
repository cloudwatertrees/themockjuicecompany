"""vc_transplant: B's top band continues A; A's right bank ends at a tip under a transplanted grass lip.

Rebuilds VARIANT_DIR/B_seam.png and VARIANT_DIR/edits.npz from ../../A.png and ../base/B_warp.png (run from anywhere).

Every edit is built from the art's own pixels (A or B; translations, one <=4 % scale / <1 deg rotation, one <=10 %
vertical resample), colour-matched where it meets other content of the same kind (local mean + contrast over a ring
at the edit edge, propagated smoothly into the edit), and composited with a short distance-based feather.
Edits (compositing order):
  path     A's path cream continued below the seam (per-column vertical copy offsets chosen by DP so the copied
           block's first row continues A's last rows; pebbles excluded from the source), feathered into B's path.
  pebble   the cut pebble (A x 558-605) closed with the bottom arc of A's own upper pebble (A x 445-491, y 1539+).
  left     B's tree canopy resampled 12 rows down (rows 0-130, x < 392, fading out by x 420) so its clumps get rounded
           tops; A's bush / boulder base / grass continued above them (DP copy, boulder and flowers excluded).
  boulder  A's boulder closed: its own lower-right arc (x 236-258, last 12 rows) translated left/down along the cut,
           soft contact shadow on the grass under it.
  bank     A's bank + verge continued (one block of A rows 1572-1677, per-row shifted so the path edge stays at
           x 665), its outer scalloped edge strip slid inward row by row along the lip outline, so the bank
           narrows to a tip at the path edge.
  lip      the top-left grass shoulder of B's lower-right island (B_warp x 512-645, y 850-968; the artist's own
           "bank ends under a grass lip" corner), own orientation, scale 1.04, rotation 0.7 deg, placed so its outline
           runs from A's verge (x 748, y 30) to the path edge (x 666, y 112); B's top-right bushes stay in front.
  pine     A's pine continued (DP copy) down to rounded bush tops of B's top-right bushes.
  seam     exponential feather (tau 2 px, rows 0-9) of the remaining row-0 residual against A's last row.
"""
import os
import numpy as np
import cv2
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
SEAM = os.path.dirname(HERE)
ROOT = os.path.dirname(SEAM)
W, H = 937, 1678
LUM = np.array([0.299, 0.587, 0.114])
R = 24                                      # A rows prepended for edge matching across the seam


def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float64)


A = load(os.path.join(ROOT, 'A.png'))
B0 = load(os.path.join(SEAM, 'base', 'B_warp.png'))
LA = A @ LUM
LB0 = B0 @ LUM
YS = np.arange(H)[:, None]
XS = np.arange(W)[None, :]


# ---------------------------------------------------------------------------------------------------------- helpers
def gauss(img, s):
    if img.ndim == 3:
        return np.stack([ndi.gaussian_filter(img[..., c], s, mode='nearest') for c in range(img.shape[2])], -1)
    return ndi.gaussian_filter(img, s, mode='nearest')


def feather(mask, f):
    """Alpha from a bool mask: linear over f px centred on the mask edge (alpha >= 0.5 exactly on the mask)."""
    m = mask.astype(bool)
    if not m.any():
        return np.zeros(m.shape)
    din = ndi.distance_transform_edt(m)
    dout = ndi.distance_transform_edt(~m)
    sd = np.where(m, din - 0.5, -(dout - 0.5))
    return np.clip(0.5 + sd / f, 0, 1)


def col_mask(c, x0, x1, top=None):
    """Bool mask of rows [top(x), c(x)) for x in [x0, x1)."""
    m = np.zeros((H, W), bool)
    for i, x in enumerate(range(x0, x1)):
        t = 0 if top is None else int(top[i])
        m[t:int(c[i]), x] = True
    return m


def hcut(cost, lo, hi, step=1, lam=0.4):
    """Min-cost horizontal path c(x) through cost[y, x], lo(x) <= c(x) <= hi(x), |dc| <= step per column."""
    Hh, Wd = cost.shape
    cost = cost.copy()
    ys = np.arange(Hh)[:, None]
    cost[(ys < lo[None, :]) | (ys > hi[None, :])] = 1e6
    acc = cost[:, 0].copy()
    back = np.zeros((Hh, Wd), np.int16)
    for x in range(1, Wd):
        best = np.full(Hh, np.inf)
        arg = np.zeros(Hh, np.int16)
        for s in range(-step, step + 1):
            if s > 0:
                sh = np.r_[np.full(s, np.inf), acc[:-s]]
            elif s < 0:
                sh = np.r_[acc[-s:], np.full(-s, np.inf)]
            else:
                sh = acc
            p = sh + lam * abs(s)
            b = p < best
            best[b] = p[b]
            arg[b] = s
        acc = best + cost[:, x]
        back[:, x] = arg
    c = np.zeros(Wd, int)
    c[-1] = int(np.argmin(acc))
    for x in range(Wd - 1, 0, -1):
        c[x - 1] = c[x] - back[c[x], x]
    return c


def dp_offsets(x0, x1, Pmin, Pmax, h, lam=2.0, ctx=3, forbid=None, dx=0):
    """Per-column vertical copy offset P(x) for B[y, x] = A[H - P + y, x], y < h <= P: the ctx rows above the copied
    block should match A's last ctx rows (so the block's first row is a plausible successor of A's last row);
    blocks touching `forbid` are excluded; P changes by <= 1 per column (penalty lam)."""
    Ps = np.arange(max(Pmin, h), Pmax + 1)
    xs = np.arange(x0, x1)
    cost = np.zeros((len(Ps), len(xs)))
    for i, P in enumerate(Ps):
        cost[i] = np.abs(LA[H - ctx:H, xs] - LA[H - ctx - P:H - P, xs + dx]).mean(0)
        if forbid is not None:
            cost[i] += 1e3 * forbid[H - P:H - P + h, xs + dx].any(0)
    c = hcut(cost, np.zeros(len(xs), int), np.full(len(xs), len(Ps) - 1), step=1, lam=lam)
    return Ps[c]


def copy_layer(Px, x0, x1, h, dx=0, base=None):
    lay = (B0 if base is None else base).copy()
    for i, x in enumerate(range(x0, x1)):
        lay[:h, x] = A[H - Px[i]:H - Px[i] + h, x + dx]
    return lay


def match(layer, canvas, alpha, use=None, ring=5, s1=5.0, s2=16.0, gain=True, gclip=(0.8, 1.25), seam=True,
          decay=None):
    """Local mean + contrast match of `layer` to `canvas` at the alpha = 0.5 edge.

    Inner ring: edit pixels within `ring` px of the edge; outer ring: canvas pixels within `ring` px (A's last R rows
    count as outside, so continuations of A are matched to A across the seam). `use` (bool, B-sized) limits which
    stretches of the edge are trusted (e.g. cream against cream, not grass against bush). The correction (offset +
    gain about the local mean) is propagated into the edit by normalised Gaussian smoothing."""
    EL = np.vstack([A[-R:], layer])
    EC = np.vstack([A[-R:], canvas])
    inside = np.vstack([np.zeros((R, W), bool), alpha >= 0.5])
    din = ndi.distance_transform_edt(inside)
    dout = ndi.distance_transform_edt(~inside)
    ri = inside & (din <= ring)
    ro = (~inside) & (dout <= ring)
    if use is not None:
        ub = ndi.binary_dilation(use, iterations=ring + 1) if use.any() else use.copy()
        if seam:
            ub[:ring + 1] = True
        Eu = np.vstack([np.full((R, W), seam), ub])
        ri &= Eu
        ro &= Eu

    def nmean(img, m, s):
        num = gauss(img * m[..., None], s)
        den = gauss(m.astype(float), s)
        return num / np.maximum(den, 1e-6)[..., None], den

    muL, dL = nmean(EL, ri, s1)
    muC, dC = nmean(EC, ro, s1)
    valid = (dL > 0.02) & (dC > 0.02) & (ri | ro)
    if not valid.any():
        return layer
    if gain:
        m2L, _ = nmean(EL ** 2, ri, s1)
        m2C, _ = nmean(EC ** 2, ro, s1)
        g = np.clip(np.sqrt(np.maximum(m2C - muC ** 2, 1.0) / np.maximum(m2L - muL ** 2, 1.0)), *gclip)
    else:
        g = np.ones_like(muL)
    wv = valid.astype(float)

    def prop(f):
        res = []
        for s in (s2, 4 * s2):
            num = gauss(f * wv[..., None], s)
            den = gauss(wv, s)
            res.append((num / np.maximum(den, 1e-9)[..., None], den))
        (f1, d1), (f2, _) = res
        t = np.clip(d1 / 0.02, 0, 1)[..., None]
        return t * f1 + (1 - t) * f2

    D, G, M = prop(muC - muL), prop(g), prop(muL)
    if decay is not None:
        k = np.exp(-ndi.distance_transform_edt(~valid) / decay)[..., None]
        D, G = D * k, 1 + (G - 1) * k
    return np.clip((M + G * (EL - M) + D)[R:], 0, 255)


def comp(canvas, layer, alpha):
    return canvas * (1 - alpha[..., None]) + layer * alpha[..., None]


def cream_mask(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    return (r > 215) & (g > 195) & (b > 160) & (r - b < 70) & (r >= g)


def domes(x0, x1, base, rng, centres_from=None, hmin=4, hmax=12, wmin=11, wmax=17, spacing=24):
    """Scalloped top outline c(x) (row of the first foliage pixel): a run of elliptic arcs over a base row."""
    n = x1 - x0
    c = np.full(n, float(base))
    xs = np.arange(n)
    cx = -rng.uniform(0, spacing)
    while cx < n + spacing:
        w = rng.uniform(wmin, wmax)
        hgt = rng.uniform(hmin, hmax)
        if centres_from is not None:
            k = int(np.clip(round(cx), 0, n - 1))
            hgt = hmin + (hmax - hmin) * centres_from[k]
        t = np.clip(1 - ((xs - cx) / w) ** 2, 0, None)
        c = np.minimum(c, np.where(t > 0, base - hgt * np.sqrt(t), base))
        cx += spacing * rng.uniform(0.8, 1.2)
    return np.round(c).astype(int)


def vresample(img, x0, x1, d_of_x, Hc):
    """Resample rows 0..Hc of columns x0..x1 down by d(x) (row y <- row (y - d) * Hc / (Hc - d)); rows < d -> NaN."""
    out = img.copy()
    for i, x in enumerate(range(x0, x1)):
        d = d_of_x[i]
        if d <= 0.01:
            continue
        y = np.arange(Hc, dtype=np.float64)
        src = (y - d) * Hc / (Hc - d)
        ok = src >= 0
        for ch in range(3):
            col = img[:Hc + 4, x, ch]
            out[:Hc, x, ch] = np.where(ok, np.interp(np.clip(src, 0, None), np.arange(Hc + 4), col), np.nan)
    return out


# ------------------------------------------------------------------------------------------------------- the edits
def build():
    out = B0.copy()
    edits = {}
    rng = np.random.default_rng(11)
    r, g, b = A[..., 0], A[..., 1], A[..., 2]
    cream_A = cream_mask(A)
    pebble_A = ndi.binary_dilation(cream_mask(A + 14) & (LA < 230) & (XS > 370) & (XS < 650), iterations=3)
    lav_A = (b > g - 8) & (b > 120) & ~cream_A
    flower_A = ((r > 170) & (b > 170) & (g < 175)) | ((r > 225) & (g > 190) & (b < 130)) | \
               ((r > 232) & (g > 232) & (b > 220))
    grey_A = ((A.max(-1) - A.min(-1)) < 28) & ~cream_A
    pink_A = (r > g + 15) & (b > g - 5)
    excl_left = ndi.binary_dilation(lav_A | flower_A | grey_A | pink_A, iterations=4)

    # ------------------------------------------------------------------ path
    x0, x1 = 384, 630
    Px = dp_offsets(x0, x1, 40, 130, 50, lam=3.0, forbid=pebble_A)
    lay = copy_layer(Px, x0, x1, 50)
    t = np.linspace(0, 1, x1 - x0)
    cp = np.round(30 + 9 * np.sin(2 * np.pi * (t * 1.7 + 0.15)) + 5 * np.sin(2 * np.pi * (t * 4.3 + 0.6))).astype(int)
    m = col_mask(cp, x0, x1)
    a = feather(m, 6)
    use = np.zeros((H, W), bool)
    use[:60, x0 + 14:x1 - 4] = True
    lay = match(lay, out, a, use=use, ring=6, s2=20)
    out = comp(out, lay, a)
    edits['path'] = a

    # ------------------------------------------------------------------ pebble
    dxp, sy0, hh = 114, 1539, 12
    lay = out.copy()
    lay[:hh, 440 + dxp:497 + dxp] = A[sy0:sy0 + hh, 440:497]
    src = (LA[sy0:sy0 + hh, 440:497] < 231)
    src = ndi.binary_dilation(src, iterations=3)
    pm = np.zeros((H, W), bool)
    pm[:hh, 440 + dxp:497 + dxp] = src
    a = feather(pm, 2.0)
    lay = match(lay, out, a, use=ndi.binary_dilation(pm, iterations=4) & ~pm, ring=3, s2=6, gain=False)
    out = comp(out, lay, a)
    edits['pebble'] = a

    # ------------------------------------------------------------------ left: A above rounded canopy tops
    x1l = 392
    lit = gauss(out @ LUM, 1.0)[8:26, :x1l] > 182
    cover = ndi.uniform_filter1d(lit.mean(0), 15)
    cl = domes(0, x1l, 27, rng, centres_from=np.clip(cover / max(cover.max(), 1e-6), 0, 1), hmin=6, hmax=18)
    acopy = B0.copy()
    for (sx0, sx1, sdx) in [(0, 209, 0), (203, 268, 58), (262, x1l, 0)]:
        Pl = dp_offsets(sx0, sx1, 30, 140, 30, lam=2.0, forbid=excl_left, dx=sdx)
        sec = copy_layer(Pl, sx0, sx1, 30, dx=sdx)
        wx = np.clip(np.minimum(XS - sx0, sx1 - 1 - XS) / 6.0, 0, 1) * ((XS >= sx0) & (XS < sx1))
        if sx0 == 0:
            wx = ((XS < sx1) * np.clip((sx1 - 1 - XS) / 6.0, 0, 1)).astype(float)
        if sx1 == x1l:
            wx = ((XS >= sx0) * np.clip((XS - sx0) / 6.0, 0, 1)).astype(float)
        wx = np.broadcast_to(wx, (H, W)).astype(float)
        if sx0 == 0:
            acopy = sec
        else:
            acopy = comp(acopy, sec, wx)
    am = col_mask(cl, 0, x1l)
    a = feather(am, 2.0)
    acopy = match(acopy, out, a, use=np.zeros((H, W), bool), ring=6, s2=18)
    out = comp(out, acopy, a)
    edits['left'] = a

    # ------------------------------------------------------------------ boulder: contact shadow under its base
    # A's boulder already closes in A's last rows (its lavender ends at y 1674-1675 above green tufts, x 207..245),
    # so nothing is added to the rock itself: the continued grass under it gets the rock's soft contact shadow.
    cx, cy, rx, ry = 226.0, -1.0, 22.0, 6.0
    shadow = ((((XS - cx) / rx) ** 2 + ((YS - cy) / ry) ** 2) <= 1.0) & (YS >= 0) & am
    sa = gauss(shadow.astype(float), 2.0) * 0.16 * (YS >= 0)
    out = out * (1 - sa[..., None])
    edits['boulder'] = np.clip(sa / 0.08, 0, 1)

    # ------------------------------------------------------------------ bank + lip
    brown = (r > g + 12) & (r < 215)

    def inner(y):
        row = brown[y, 600:720]
        for i in range(len(row) - 6):
            if row[i:i + 6].all():
                return 600 + i
        return 665

    hb = 118                                                            # copied rows
    Apad = np.pad(A, ((0, 0), (8, 8), (0, 0)), mode='edge')
    LApad = Apad @ LUM
    best = None
    for P in range(hb, 160):
        cst = 0.0
        for k in range(3):
            sh = 665 - inner(H - P - 3 + k)
            cst += np.abs(LA[H - 3 + k, 640:900] - LApad[H - P - 3 + k, 640 - sh + 8:900 - sh + 8]).mean() / 3
        if best is None or cst < best[0]:
            best = (cst, P)
    Pb = best[1]
    bank = out.copy()
    x0 = 618
    shifts = ndi.gaussian_filter1d(np.array([665.0 - inner(min(H - 1, H - Pb + y)) for y in range(-12, hb + 12)]), 6.0)[12:-12]
    xsrc = np.arange(x0, W, dtype=np.float64)
    for y in range(hb):
        sy = H - Pb + y
        for ch in range(3):
            bank[y, x0:W, ch] = np.interp(xsrc - shifts[y] + 8, np.arange(W + 16), Apad[sy, :, ch])

    # lip geometry: source shoulder outline -> target (similarity from two outline points)
    s1, s2 = np.array([595.0, 875.0]), np.array([517.0, 955.0])
    t1, t2 = np.array([748.0, 30.0]), np.array([660.0, 108.0])
    vs, vt = s2 - s1, t2 - t1
    sc = np.linalg.norm(vt) / np.linalg.norm(vs)
    ang = np.arctan2(vt[1], vt[0]) - np.arctan2(vs[1], vs[0])
    Rm = sc * np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
    M = np.hstack([Rm, (t1 - Rm @ s1)[:, None]])
    lipl = cv2.warpAffine(B0.astype(np.float32), M, (W, H), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REFLECT).astype(np.float64)
    win = np.zeros((H, W), np.uint8)
    win[846:968, 505:665] = 1
    grass_s = (win > 0) & ~ndi.binary_dilation(cream_mask(B0), iterations=1)
    grass_s = ndi.binary_opening(grass_s, iterations=1)
    grass_f = cv2.warpAffine(grass_s.astype(np.float32), M, (W, H), flags=cv2.INTER_LINEAR)
    grass_t = gauss(grass_f.astype(np.float64), 1.2) > 0.5                 # smooth transplanted outline
    rim = {}
    for y in range(0, 140):
        idx = np.flatnonzero(grass_t[y, 600:830])
        if idx.size:
            rim[y] = 600 + idx[0]
    ytop, ytip = 30, 112
    rim_x = np.array([rim.get(y, 999) for y in range(140)], float)
    rim_s = ndi.gaussian_filter1d(np.where(rim_x < 999, rim_x, 760), 1.0)

    # right-top region: bank above the outline; verge + pine down to rounded tops of B's bushes
    bmask = np.zeros((H, W), bool)
    for y in range(hb):
        xr = 742 if y < ytop else min(742, int(round(rim_s[y])) + 3)
        if y >= ytop and rim_s[y] < 664:
            xr = 0                                                      # past the tip: path only
        bmask[y, 660:max(660, xr)] = True
    tc = np.linspace(0, 1, 664 - x0)
    cend = np.round(hb - 4 - 14 * tc ** 0.7 + 3 * np.sin(2 * np.pi * (tc * 2.3 + 0.2))).astype(int)
    bmask |= col_mask(cend, x0, 664)                                   # path cream beside the bank, ragged end
    flowerB = ((B0[..., 0] > 225) & (B0[..., 1] > 190) & (B0[..., 2] < 140)) | \
              ((B0[..., 0] > 235) & (B0[..., 1] > 235) & (B0[..., 2] > 225))
    xr0 = 742
    cpn = domes(xr0, W, 30, rng, hmin=8, hmax=16, wmin=10, wmax=15, spacing=22)
    lab, n = ndi.label(ndi.binary_dilation(flowerB[:60, xr0:W], iterations=3))
    for k in range(1, n + 1):
        yy, xx = np.nonzero(lab == k)
        if yy.min() < 14:
            cpn[xx.min():xx.max() + 1] = np.maximum(cpn[xx.min():xx.max() + 1], yy.max() + 3)
        else:
            cpn[xx.min():xx.max() + 1] = np.minimum(cpn[xx.min():xx.max() + 1], yy.min() - 1)
    cpn = np.clip(cpn, 10, 44)
    cpn[:768 - xr0] = np.maximum(cpn[:768 - xr0], ytop + 2)
    bmask |= col_mask(cpn, xr0, W)
    a_bank = feather(bmask, 2.5)
    bank = match(bank, out, a_bank, use=np.zeros((H, W), bool), ring=6, s2=18)
    use = np.zeros((H, W), bool)
    use[20:hb + 6, x0 - 4:x0 + 8] = True
    use[hb - 26:hb + 6, x0:662] = True
    bank = match(bank, out, a_bank, use=use, ring=6, s2=12, seam=False, decay=14.0)
    # shadow of the grass lip on the bank, just above the outline
    lipsh = np.zeros((H, W))
    for y in range(ytop - 4, ytip + 4):
        xr = rim_s[y]
        xx = np.arange(600, 760)
        lipsh[y, 600:760] = np.clip(1 - (xr - xx) / 6.0, 0, 1) * (xx < xr + 1)
    bank = bank * (1 - 0.16 * gauss(lipsh, 1.0)[..., None])
    out = comp(out, bank, a_bank)
    edits['bank'] = a_bank

    # lip grass: grass side of the outline, a band <= 30 px, B's top-right bush clusters stay in front
    leafB = (B0[..., 1] - B0[..., 0] > 18) & (LB0 < 175)
    leafB = ndi.binary_opening(ndi.binary_closing(leafB, iterations=3), iterations=2)
    lab, n = ndi.label(leafB)
    sizes = ndi.sum(leafB, lab, range(1, n + 1))
    bushB = np.isin(lab, 1 + np.flatnonzero(sizes > 600)) & (YS > ytop + 8)
    outline = np.zeros((H, W), bool)
    for y, x in rim.items():
        outline[y, x] = True
    band = ndi.distance_transform_edt(~outline) <= 30
    lm = ndi.binary_erosion(grass_t, iterations=2) & band & (YS < 130) & (XS < 800) & ~bushB & (YS >= ytop - 4)
    a_lip = feather(lm, 2.5)
    Lo = out @ LUM
    grassy = (out[..., 1] > out[..., 0] + 4) & (out[..., 1] > out[..., 2] + 30) & (Lo > 165)
    far = ~ndi.binary_dilation(outline, iterations=5) & ~bushB & grassy
    lipl = match(lipl, out, a_lip, use=far, ring=5, s2=14, seam=False)
    out = comp(out, lipl, a_lip)
    edits['lip'] = a_lip

    # ------------------------------------------------------------------ seam feather
    res = gauss(A[-1][None] - out[0][None], 1.5)[0]
    wy = np.exp(-np.arange(12) / 2.5)
    out[:12] += wy[:, None, None] * res[None]
    sa = np.zeros((H, W))
    sa[:12] = wy[:, None]
    edits['seam'] = sa

    out = np.clip(out, 0, 255)
    assert np.abs(out[500:] - B0[500:]).max() < 1e-6
    return out, edits


def main():
    out, edits = build()
    Image.fromarray(np.round(out).astype(np.uint8)).save(os.path.join(HERE, 'B_seam.png'))
    np.savez(os.path.join(HERE, 'edits.npz'), **{k: v.astype(np.float32) for k, v in edits.items()})
    print('wrote B_seam.png, edits.npz:', ', '.join(edits))


if __name__ == '__main__':
    main()
