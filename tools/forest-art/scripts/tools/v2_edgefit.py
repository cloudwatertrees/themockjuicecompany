"""v2: analysis-by-synthesis boundary refinement of the 4x label map (between pb_refine.py and pb_trace.py).
Each 1x pixel is modelled as the mean of its 16 sub-pixels' region colours (the renderer's coverage-weighted blend);
region colours are pb_refine's local fields (normalised convolution of the region's 1x interior). Boundary sub-pixels
take a neighbouring label when that lowers the squared error of their 1x pixel against the reference by more than
lam x the added boundary length. Only hard and soft-edge boundaries move (smooth ones stay indicator-placed), only
within 1 px of the existing boundary. Moves geometry only: no colour or detail is added.
With DATADIR and SHAPES_JSON (a fitted pass of the same SRC), region colours are the fitted mesh fills instead, so
the model is the actual render; alternate fit and this step.
V2_CLEAN=1: then a 5x5 majority filter on the boundary band and removal of islands under 24 sub-pixels.
usage: v2_edgefit.py SRC DST [lam] [iters] [DATADIR SHAPES_JSON]   (SRC/DST are out/B/TAG bases; DST gets
_reg/_layer/_pairs/_cell/_reg4)"""
import sys, shutil, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from art import W, H
from score import SP
U, K = 4, 8
HARD, SOFT, SMOOTH = 0, 1, 2

src, dst = sys.argv[1], sys.argv[2]
lam = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0
iters = int(sys.argv[4]) if len(sys.argv) > 4 else 6
for f in ('reg', 'layer', 'pairs', 'cell'):
    if src != dst: shutil.copy(src + '_%s.npy' % f, dst + '_%s.npy' % f)
reg = np.load(src + '_reg.npy'); lab4 = np.load(src + '_reg4.npy').astype(np.int32); P = np.load(src + '_pairs.npy')
ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float32)
n = int(max(reg.max(), lab4.max())) + 1

# boundary classes by label pair (pairs absent at 1x count as hard, as in pb_refine)
lo, hi = np.minimum(P[:, 0], P[:, 1]).astype(np.int64), np.maximum(P[:, 0], P[:, 1]).astype(np.int64)
keys = lo * n + hi; order = np.argsort(keys); keys, kcls = keys[order], P[order, 2].astype(np.int8)
def movable(a, b):
    q = np.minimum(a, b).astype(np.int64) * n + np.maximum(a, b)
    i = np.clip(np.searchsorted(keys, q), 0, len(keys) - 1)
    return np.where(keys[i] == q, kcls[i], HARD) != SMOOTH

# band: 1x pixels whose 4x block is mixed, plus 1 px
e = np.zeros_like(reg, bool)
e[:, 1:] |= reg[:, 1:] != reg[:, :-1]; e[:, :-1] |= reg[:, 1:] != reg[:, :-1]
e[1:] |= reg[1:] != reg[:-1]; e[:-1] |= reg[1:] != reg[:-1]
inner = ~e
blk = lab4.reshape(H, U, W, U)
band = ndi.binary_dilation((blk != blk[:, :1, :, :1]).any((1, 3)), iterations=1)

# fitted fills by region (largest shape of each region), matched to the shapes file by path
fills = {}
if len(sys.argv) > 6:
    import json
    from pbart import load
    by_path = {}
    for s_ in json.load(open(sys.argv[6])): by_path.setdefault(s_['path'], []).append(s_['region'])
    for sh in load(sys.argv[5]):
        rs = by_path.get(sh.pathstr)
        if not rs: continue
        area = (sh.box[2] - sh.box[0]) * (sh.box[3] - sh.box[1])
        if rs[0] not in fills or area > fills[rs[0]][0]: fills[rs[0]] = (area, sh)
    print('fitted fills for %d regions' % len(fills))

# per band pixel: up to K candidate labels with their local colour
slot_lab = np.full((H, W, K), -1, np.int32); slot_col = np.zeros((H, W, K, 3), np.float32); nslot = np.zeros((H, W), np.int16)
objs1, objs4 = ndi.find_objects(reg + 1), ndi.find_objects(lab4 + 1)
over = 0
for r in range(n):
    s1 = objs1[r] if r < len(objs1) else None; s4 = objs4[r] if r < len(objs4) else None
    if s4 is None: continue
    ys = [s4[0].start // U, -(-s4[0].stop // U)]; xs = [s4[1].start // U, -(-s4[1].stop // U)]
    if s1 is not None:
        ys = [min(ys[0], s1[0].start), max(ys[1], s1[0].stop)]; xs = [min(xs[0], s1[1].start), max(xs[1], s1[1].stop)]
    y0, y1, x0, x1 = max(ys[0] - 3, 0), min(ys[1] + 3, H), max(xs[0] - 3, 0), min(xs[1] + 3, W)
    pres = (lab4[y0 * U:y1 * U, x0 * U:x1 * U] == r).reshape(y1 - y0, U, x1 - x0, U).any((1, 3))
    pres = ndi.binary_dilation(pres, structure=np.ones((3, 3), bool)) & band[y0:y1, x0:x1]
    if not pres.any(): continue
    m = reg[y0:y1, x0:x1] == r; sub = ref[y0:y1, x0:x1]
    if not m.any(): m = (lab4[y0 * U:y1 * U, x0 * U:x1 * U] == r).reshape(y1 - y0, U, x1 - x0, U).mean((1, 3)) >= 0.5
    if not m.any(): m = pres
    mi = (m & inner[y0:y1, x0:x1]).astype(np.float32)
    thick = ndi.distance_transform_edt(np.pad(m, 1))[1:-1, 1:-1].max()
    if r in fills:
        gy, gx = np.mgrid[y0:y1, x0:x1]
        F = fills[r][1].colour_at(gx + 0.5, gy + 0.5) * 255
    elif thick <= 1.5 or mi.sum() < 3:
        ring = ndi.binary_dilation(m, iterations=2) & ~m
        bg = sub[ring].mean(0) if ring.any() else sub[m].mean(0)
        px = sub[m]; d = np.linalg.norm(px - bg, axis=1)
        F = np.broadcast_to(px[d >= np.percentile(d, 70)].mean(0), sub.shape)
    else:
        num = np.stack([ndi.gaussian_filter(sub[..., c] * mi, 1.5, mode='constant') for c in range(3)], -1)
        den = ndi.gaussian_filter(mi, 1.5, mode='constant')[..., None]
        F = num / np.maximum(den, 1e-3); F[den[..., 0] < 1e-3] = sub[m].mean(0)
    py, px_ = np.nonzero(pres); Y, X = py + y0, px_ + x0
    k = nslot[Y, X]; ok = k < K; over += (~ok).sum()
    slot_lab[Y[ok], X[ok], k[ok]] = r; slot_col[Y[ok], X[ok], k[ok]] = F[py[ok], px_[ok]]; nslot[Y[ok], X[ok]] += 1
print('band px %d, slot overflow %d, lam %.1f' % (band.sum(), over, lam))

by, bx = np.nonzero(band)
SL, SC, R = slot_lab[by, bx], slot_col[by, bx], ref[by, bx]
del slot_lab, slot_col
def slot_of(L):
    hit = SL == L[:, None]
    return np.where(hit.any(1), hit.argmax(1), -1)
# freeze pixels with a sub-pixel label missing from their slots
sub_lab = lab4.reshape(H, U, W, U)[by, :, bx, :].reshape(len(by), U * U)
sub_slot = np.stack([slot_of(sub_lab[:, j]) for j in range(U * U)], 1)
live = (sub_slot >= 0).all(1)
by, bx, SL, SC, R, sub_slot = by[live], bx[live], SL[live], SC[live], R[live], sub_slot[live]
C = np.take_along_axis(SC, sub_slot[..., None].repeat(3, 2), 1).mean(1)
ar = np.arange(len(by))
print('live px %d, start rms %.3f' % (len(by), np.sqrt(((C - R) ** 2).sum(1).mean())))
H4, W4 = H * U, W * U
DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))
for it in range(iters):
    nflip = 0
    for a in range(U):
        for b in range(U):
            yy, xx = by * U + a, bx * U + b
            cur = lab4[yy, xx]
            nb = np.stack([lab4[np.clip(yy + dy, 0, H4 - 1), np.clip(xx + dx, 0, W4 - 1)] for dy, dx in DIRS], 1)
            sc = slot_of(cur); Fc = SC[ar, sc]
            e0 = ((C - R) ** 2).sum(1); dcur = (nb != cur[:, None]).sum(1)
            best, bestL, bestF = np.zeros(len(by), np.float32), cur.copy(), Fc
            for d in range(4):
                L = nb[:, d]; sL = slot_of(L)
                ok = (L != cur) & (sL >= 0) & movable(cur, L)
                FL = SC[ar, np.maximum(sL, 0)]
                dE = ((C + (FL - Fc) / (U * U) - R) ** 2).sum(1) - e0 + lam * ((nb != L[:, None]).sum(1) - dcur)
                take = ok & (dE < best - 1e-6)
                best = np.where(take, dE, best); bestL = np.where(take, L, bestL); bestF = np.where(take[:, None], FL, bestF)
            mv = bestL != cur
            lab4[yy[mv], xx[mv]] = bestL[mv]; C[mv] += (bestF[mv] - Fc[mv]) / (U * U); nflip += mv.sum()
    print('iter %d: flips %d, rms %.3f' % (it, nflip, np.sqrt(((C - R) ** 2).sum(1).mean())))
    if nflip == 0: break
if __import__('os').environ.get('V2_CLEAN', '0') == '1':   # majority filter on the boundary band + islands under 1.5 px^2
    from pb_refine import cleanup
    lab4 = cleanup(lab4, np.repeat(np.repeat(band, U, 0), U, 1), iters=1, min_island=24)
np.save(dst + '_reg4.npy', lab4.astype(np.int16))
