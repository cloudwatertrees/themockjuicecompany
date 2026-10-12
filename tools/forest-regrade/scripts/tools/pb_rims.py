"""Rim (outline stroke) synthesis on the 4x label map. For every hard boundary between a later region F and an
earlier region B, the mean reference cross-profile is compared with a plain step; a consistent bump (light or dark
line) becomes a continuous band region at the measured offset/width along that boundary, drawn right after F."""
import sys, numpy as np
from scipy import ndimage as ndi
from PIL import Image
from skimage.color import rgb2lab
from art import W, H
SP = '/tmp/work/'
U = 4

def detect(lab4, order_rank, rl, min_pts=12, thr=3.5):
    """Return list of (F, B, side, o1, o2) rims; side +1 = band in B (outside F), -1 = band in F. Offsets in units."""
    Hh, Ww = lab4.shape
    # boundary pixel pairs at 4x (horizontal + vertical)
    pairs = []
    for (a, b, dy, dx) in [(lab4[:, :-1], lab4[:, 1:], 0, 1), (lab4[:-1], lab4[1:], 1, 0)]:
        ys, xs = np.nonzero(a != b)
        pairs.append((ys, xs, ys + dy, xs + dx))
    Y0 = np.concatenate([p[0] for p in pairs]); X0 = np.concatenate([p[1] for p in pairs])
    Y1 = np.concatenate([p[2] for p in pairs]); X1 = np.concatenate([p[3] for p in pairs])
    la, lb = lab4[Y0, X0], lab4[Y1, X1]
    # orient: F = later (higher rank) region
    swap = order_rank[la] < order_rank[lb]
    F = np.where(swap, lb, la); B = np.where(swap, la, lb)
    # point on boundary (design units) and normal pointing from F into B
    fy = np.where(swap, Y1, Y0); fx = np.where(swap, X1, X0); by = np.where(swap, Y0, Y1); bx = np.where(swap, X0, X1)
    cy = (fy + by) / 2 + 0.5; cx = (fx + bx) / 2 + 0.5
    ny = (by - fy).astype(float); nx = (bx - fx).astype(float)
    key = F.astype(np.int64) * (lab4.max() + 1) + B
    uk, inv = np.unique(key, return_inverse=True)
    t = np.arange(-3.0, 3.01, 0.25)            # design units along the normal (F side negative)
    rims = []
    order_i = np.argsort(inv, kind='stable'); splits = np.nonzero(np.diff(inv[order_i]))[0] + 1
    for g in np.split(order_i, splits):
        if len(g) < min_pts * U: continue
        g = g[::2]
        py = (cy[g][:, None] / U) + ny[g][:, None] * t[None]; px = (cx[g][:, None] / U) + nx[g][:, None] * t[None]
        prof = np.stack([ndi.map_coordinates(rl[..., c], [py - 0.5, px - 0.5], order=3, mode='nearest') for c in range(3)], -1).mean(0)
        a_side, b_side = prof[t <= -2].mean(0), prof[t >= 2].mean(0)
        # step model with the edge at the colour midpoint crossing
        v = b_side - a_side; vv = v @ v
        if vv < 4: continue
        proj = (prof - a_side) @ v / vv
        k = np.argmin(np.abs(proj - 0.5)); t0 = t[k]
        step = np.where(t[:, None] < t0, a_side[None], b_side[None])
        dev = np.linalg.norm(prof - step, axis=1)
        near = np.abs(t - t0) <= 1.75
        dev_n = np.where(near, dev, 0)
        # exclude the transition itself (within +-0.5 of t0): a rim is a bump beyond the step
        core = np.abs(t - t0) <= 0.5
        side_b = near & ~core & (t > t0); side_f = near & ~core & (t < t0)
        for side, msk in ((+1, side_b), (-1, side_f)):
            if not msk.any(): continue
            # bump must exceed both plateaus (not just an intermediate AA value)
            plate = b_side if side > 0 else a_side
            other = a_side if side > 0 else b_side
            vals = prof[msk]
            d_plate = np.linalg.norm(vals - plate, axis=1); d_other = np.linalg.norm(vals - other, axis=1)
            beyond = (d_plate > thr) & (d_other > d_plate * 0.6)
            # must not lie on the A-B segment (intermediate colour)
            tt = (vals - a_side) @ v / vv
            inter = (tt > -0.15) & (tt < 1.15) & (np.linalg.norm(vals - (a_side + np.clip(tt, 0, 1)[:, None] * v), axis=1) < thr)
            ok = beyond & ~inter
            if ok.sum() >= 2:
                ts = t[msk][ok]
                o1, o2 = ts.min() - 0.125, ts.max() + 0.125
                rims.append((int(F[g[0]]), int(B[g[0]]), side, float(o1 - t0) * side, float(o2 - t0) * side, float(t0)))
    return rims

def build(lab4, rims, n_regions):
    """Add rim band regions (new ids) to the 4x label map."""
    out = lab4.copy(); new = []
    objs = ndi.find_objects(lab4 + 1)
    for k, (F, B, side, o1, o2, t0) in enumerate(rims):
        o1, o2 = max(min(o1, o2), 0.0), max(o1, o2)
        if o2 - o1 < 0.5: o2 = o1 + 0.5
        slF, slB = objs[F], objs[B]
        if slF is None or slB is None: continue
        y0 = max(min(slF[0].start, slB[0].start) - 16, 0); y1 = min(max(slF[0].stop, slB[0].stop) + 16, lab4.shape[0])
        x0 = max(min(slF[1].start, slB[1].start) - 16, 0); x1 = min(max(slF[1].stop, slB[1].stop) + 16, lab4.shape[1])
        win = lab4[y0:y1, x0:x1]
        # crop to the F|B boundary neighbourhood (rims lie within a few units of it)
        mF0, mB0 = win == F, win == B
        near = ndi.binary_dilation(mB0, structure=np.ones((3, 3), bool)) & mF0
        if not near.any(): continue
        ys_, xs_ = np.nonzero(near); pad = 24
        cy0, cy1 = max(ys_.min() - pad, 0), min(ys_.max() + pad + 1, win.shape[0]); cx0, cx1 = max(xs_.min() - pad, 0), min(xs_.max() + pad + 1, win.shape[1])
        y0, x0 = y0 + cy0, x0 + cx0; y1, x1 = y0 + (cy1 - cy0), x0 + (cx1 - cx0)
        win = lab4[y0:y1, x0:x1]
        mF, mB = win == F, win == B
        # boundary between F and B only: pixels of F adjacent to B and vice versa
        adj = ndi.binary_dilation(mB, structure=np.ones((3, 3), bool)) & mF
        adjB = ndi.binary_dilation(mF, structure=np.ones((3, 3), bool)) & mB
        if side > 0:
            d = ndi.distance_transform_edt(~adj) / U          # distance (units) from the F|B boundary, within B
            band = mB & (d >= o1 + t0 * 0) & (d <= o2)
        else:
            d = ndi.distance_transform_edt(~adjB) / U
            band = mF & (d >= o1) & (d <= o2)
        if band.sum() < 16: continue
        # smooth band edges a little
        band = ndi.binary_opening(band, structure=np.ones((2, 2), bool)) if band.sum() > 64 else band
        rid = n_regions + len(new)
        sub = out[y0:y1, x0:x1]; sub[band & (sub == (B if side > 0 else F))] = rid
        new.append((int(rid), int(F)))
    return out, new

if __name__ == '__main__':
    base = sys.argv[1]
    import json
    lab4 = np.load(base + '_reg4.npy'); reg = np.load(base + '_reg.npy'); lay = np.load(base + '_layer.npy')
    rank = np.load(base + '_rank.npy')
    rl = rgb2lab(np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255)
    rims = detect(lab4, rank, rl)
    print('rims detected', len(rims), ' outside %d inside %d' % (sum(r[2] > 0 for r in rims), sum(r[2] < 0 for r in rims)))
    out, new = build(lab4, rims, lab4.max() + 1)
    np.save(base + '_reg4r.npy', out.astype(np.int16))
    json.dump(new, open(base + '_rims.json', 'w'))
    print('rim regions', len(new), 'px', int((out != lab4).sum()))
