"""Phase B stage 3: 4x label map with sub-pixel boundaries.
Near hard/soft-edge boundaries: argmin colour distance between the bicubic-upsampled reference and each candidate
region's local colour field (normalised convolution of its interior), plus a weak geometric prior.
Near smooth boundaries: argmax of the Gaussian-smoothed 1x indicator (no staircase). Then mode filter + islands."""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2lab
from skimage.filters.rank import majority
from art import W, H
SP = '/tmp/work/'
U = 4
HARD, SOFT, SMOOTH = 0, 1, 2

def ref4_lab(ref):
    out = np.zeros((H * U, W * U, 3), np.float16)
    xs = (np.arange(W * U) + 0.5) / U - 0.5
    for y0 in range(0, H * U, 512):
        ys = (np.arange(y0, min(y0 + 512, H * U)) + 0.5) / U - 0.5
        YY, XX = np.meshgrid(ys, xs, indexing='ij')
        rgb = np.stack([ndi.map_coordinates(ref[..., c], [YY, XX], order=3, mode='nearest') for c in range(3)], -1)
        out[y0:y0 + len(ys)] = rgb2lab(np.clip(rgb, 0, 1)).astype(np.float16)
    return out

def run(base, gamma=0.3, sig_ind=float(__import__('os').environ.get('PB_SIGIND', '0.7')), sig_cost=float(__import__('os').environ.get('PB_SIGCOST', '2.0'))):
    reg = np.load(base + '_reg.npy'); P = np.load(base + '_pairs.npy')
    n = reg.max() + 1
    pcls = {}
    for a, b, c, *_ in P: pcls[(int(a), int(b))] = int(c)
    ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
    rl = rgb2lab(ref)
    R4 = ref4_lab(ref)
    # band at 1x: pixels within 1 px of a boundary
    e = np.zeros_like(reg, bool)
    e[:, 1:] |= reg[:, 1:] != reg[:, :-1]; e[:, :-1] |= reg[:, 1:] != reg[:, :-1]
    e[1:] |= reg[1:] != reg[:-1]; e[:-1] |= reg[1:] != reg[:-1]
    band1 = ndi.binary_dilation(e, iterations=int(__import__("os").environ.get("PB_BAND", "1")))
    inner = ~e
    big = np.float32(1e9)
    bc = np.full((H * U, W * U), big, np.float32); bcl = np.repeat(np.repeat(reg, U, 0), U, 1).astype(np.int16)
    bi = np.zeros((H * U, W * U), np.float16); bil = bcl.copy(); si = np.zeros((H * U, W * U), np.float16); sil = np.full((H * U, W * U), -1, np.int16)
    band4 = np.repeat(np.repeat(band1, U, 0), U, 1)
    objs = ndi.find_objects(reg + 1)
    for r in range(n):
        sl = objs[r]
        if sl is None: continue
        y0, y1 = max(sl[0].start - 3, 0), min(sl[0].stop + 3, H); x0, x1 = max(sl[1].start - 3, 0), min(sl[1].stop + 3, W)
        m = reg[y0:y1, x0:x1] == r
        dil = ndi.binary_dilation(m, structure=np.ones((3, 3), bool), iterations=int(__import__("os").environ.get("PB_BAND", "1"))) & band1[y0:y1, x0:x1]
        if not dil.any(): continue
        # local colour field: normalised convolution of interior pixels (thin regions: their most extreme colour)
        thick = ndi.distance_transform_edt(np.pad(m, 1))[1:-1, 1:-1].max()
        mi = (m & inner[y0:y1, x0:x1]).astype(float)
        sub = rl[y0:y1, x0:x1]
        if thick <= 1.5 or mi.sum() < 3:
            ring = ndi.binary_dilation(m, iterations=2) & ~m
            bg = sub[ring].mean(0) if ring.any() else sub[m].mean(0)
            px = sub[m]; d = np.linalg.norm(px - bg, axis=1)
            sel = d >= np.percentile(d, 70)
            F = np.broadcast_to(px[sel].mean(0), sub.shape).astype(np.float32)
        else:
            num = np.stack([ndi.gaussian_filter(sub[..., c] * mi, 1.5, mode='constant') for c in range(3)], -1)
            den = ndi.gaussian_filter(mi, 1.5, mode='constant')[..., None]
            F = (num / np.maximum(den, 1e-3)).astype(np.float32)
            # far from any interior pixel: fall back to the region mean
            far = den[..., 0] < 1e-3
            F[far] = sub[m].mean(0)
        ind = ndi.gaussian_filter(m.astype(np.float32), sig_ind, mode='constant')
        # dense 4x tiles: colour cost, spatially smoothed over the candidate support (smooth boundaries)
        T1, mg = 128, 3
        hh, ww = m.shape
        for ty in range(0, hh, T1):
            for tx in range(0, ww, T1):
                if not dil[ty:ty + T1, tx:tx + T1].any(): continue
                a0, a1 = max(ty - mg, 0), min(ty + T1 + mg, hh); b0, b1 = max(tx - mg, 0), min(tx + T1 + mg, ww)
                F4 = np.stack([ndi.zoom(F[a0:a1, b0:b1, c], U, order=1, grid_mode=True, mode='nearest') for c in range(3)], -1)
                I4w = ndi.zoom(ind[a0:a1, b0:b1], U, order=1, grid_mode=True, mode='nearest')
                cand = np.repeat(np.repeat(dil[a0:a1, b0:b1], U, 0), U, 1)
                Y0, X0 = (y0 + a0) * U, (x0 + b0) * U
                Rw = R4[Y0:Y0 + F4.shape[0], X0:X0 + F4.shape[1]].astype(np.float32)
                cost = ((Rw - F4) ** 2).sum(-1) + gamma * 25.0 * (1 - I4w)
                cm = cand.astype(np.float32)
                cost = ndi.gaussian_filter(cost * cm, sig_cost, mode='constant') / np.maximum(ndi.gaussian_filter(cm, sig_cost, mode='constant'), 1e-6)
                # keep the tile interior only (the margin just feeds the smoothing)
                iy0, iy1 = (ty - a0) * U, (min(ty + T1, hh) - a0) * U; ix0, ix1 = (tx - b0) * U, (min(tx + T1, ww) - b0) * U
                tile_in = np.zeros_like(cand); tile_in[iy0:iy1, ix0:ix1] = True
                ii, jj = np.nonzero(cand & tile_in)
                I4, J4 = ii + Y0, jj + X0
                cv = cost[ii, jj].astype(np.float32); Iv = I4w[ii, jj]
                better = cv < bc[I4, J4]
                bc[I4[better], J4[better]] = cv[better]; bcl[I4[better], J4[better]] = r
                # top-2 indicator bookkeeping
                cur, curl, sec = bi[I4, J4], bil[I4, J4], si[I4, J4]
                top = Iv > cur
                mid = ~top & (Iv > sec)
                si[I4[top], J4[top]] = cur[top]; sil[I4[top], J4[top]] = curl[top]
                bi[I4[top], J4[top]] = Iv[top]; bil[I4[top], J4[top]] = r
                si[I4[mid], J4[mid]] = Iv[mid]; sil[I4[mid], J4[mid]] = r
    out = bcl.copy()
    # smooth-boundary pixels: decide by indicator
    ii, jj = np.nonzero(band4 & (sil >= 0))
    a, b = bil[ii, jj], sil[ii, jj]
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    cls = np.array([pcls.get((int(p), int(q)), HARD) for p, q in zip(lo, hi)])
    sm = cls == SMOOTH
    out[ii[sm], jj[sm]] = bil[ii[sm], jj[sm]]
    print('band px %d, smooth-decided %d' % (len(ii), sm.sum()))
    return out, band4

def cleanup(lab4, band4, iters=2, min_island=12):
    """Mode filter within the band (labels remapped to local uint16 ids per tile), then remove tiny islands."""
    out = lab4.copy()
    T = 512
    for it in range(iters):
        for y0 in range(0, out.shape[0], T):
            for x0 in range(0, out.shape[1], T):
                ys, xs = slice(max(y0 - 4, 0), min(y0 + T + 4, out.shape[0])), slice(max(x0 - 4, 0), min(x0 + T + 4, out.shape[1]))
                tile = out[ys, xs]; bt = band4[ys, xs]
                if not bt.any(): continue
                u, inv = np.unique(tile, return_inverse=True)
                if len(u) < 2: continue
                maj = majority(inv.reshape(tile.shape).astype(np.uint16), np.ones((5, 5), bool))
                newt = u[maj]
                iy, ix = y0 - ys.start, x0 - xs.start
                region = (slice(iy, iy + min(T, out.shape[0] - y0)), slice(ix, ix + min(T, out.shape[1] - x0)))
                sel = bt[region]
                out[y0:y0 + sel.shape[0], x0:x0 + sel.shape[1]][sel] = newt[region][sel]
    # islands
    n_fix = 0
    for y0 in range(0, out.shape[0], T):
        for x0 in range(0, out.shape[1], T):
            ys, xs = slice(max(y0 - 8, 0), min(y0 + T + 8, out.shape[0])), slice(max(x0 - 8, 0), min(x0 + T + 8, out.shape[1]))
            tile = out[ys, xs]
            u, inv = np.unique(tile, return_inverse=True); inv = inv.reshape(tile.shape)
            for k in range(len(u)):
                cc, nc = ndi.label(inv == k)
                if nc <= 1: continue
                sz = ndi.sum(np.ones_like(cc), cc, range(1, nc + 1))
                for c in np.nonzero(sz < min_island)[0]:
                    mm = cc == c + 1
                    ring = ndi.binary_dilation(mm) & ~mm
                    vals = tile[ring]
                    if len(vals): tile[mm] = u[np.bincount(np.searchsorted(u, vals)).argmax()]; n_fix += 1
            out[ys, xs] = tile
    print('islands fixed', n_fix)
    return out

def min_width(lab4, iters=3):
    """Remove label structures thinner than ~3 px at 4x (0.75 design units): 3x3 opening per label,
    removed pixels take the label of an eroded (thick) neighbour."""
    lab = lab4.copy()
    H4, W4 = lab.shape
    for it in range(iters):
        pad = np.pad(lab, 1, mode='edge')
        same = np.ones_like(lab, bool)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                same &= pad[1 + dy:1 + dy + H4, 1 + dx:1 + dx + W4] == lab
        # opened membership: some eroded pixel of my label within 3x3
        er = np.where(same, lab, -1); pe = np.pad(er, 1, constant_values=-1)
        keep = np.zeros_like(lab, bool)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                keep |= pe[1 + dy:1 + dy + H4, 1 + dx:1 + dx + W4] == lab
        thin = ~keep
        if not thin.any(): break
        # reassign thin pixels to the label of an eroded neighbour within 5x5 (closest first)
        new = np.full_like(lab, -1); pe2 = np.pad(er, 2, constant_values=-1)
        for r in (1, 2):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if max(abs(dy), abs(dx)) != r: continue
                    cand = pe2[2 + dy:2 + dy + H4, 2 + dx:2 + dx + W4]
                    m = thin & (new < 0) & (cand >= 0)
                    new[m] = cand[m]
        fix = thin & (new >= 0)
        lab[fix] = new[fix]
        print('min_width pass %d: thin px %d, reassigned %d' % (it, thin.sum(), fix.sum()))
    return lab

def dissolve_beads(lab4, max_width=2.0, max_len=10.0):
    """Short thin pieces wedged between >= 2 regions (rim/AA beads) are split between their neighbours along
    their medial line. Isolated small features (one surrounding region) are kept."""
    from skimage.morphology import skeletonize
    lab = lab4.copy()
    objs = ndi.find_objects(lab + 1)
    nd = 0
    for r, sl in enumerate(objs):
        if sl is None: continue
        y0, y1 = max(sl[0].start - 3, 0), min(sl[0].stop + 3, lab.shape[0]); x0, x1 = max(sl[1].start - 3, 0), min(sl[1].stop + 3, lab.shape[1])
        win = lab[y0:y1, x0:x1]
        m = win == r
        comps, nc = ndi.label(m)
        for c in range(1, nc + 1):
            cm = comps == c
            hw = ndi.distance_transform_edt(np.pad(cm, 1)).max()
            if hw * 2 / U > max_width: continue
            if skeletonize(cm).sum() / U >= max_len: continue
            ring = ndi.binary_dilation(cm, structure=np.ones((3, 3), bool)) & ~cm
            nbr = np.unique(win[ring])
            nbr = nbr[nbr != r]
            if len(nbr) < 2: continue
            other = ~cm & np.isin(win, nbr)
            _, (iy, ix) = ndi.distance_transform_edt(~other, return_indices=True)
            ys, xs = np.nonzero(cm)
            win[ys, xs] = win[iy[ys, xs], ix[ys, xs]]
            nd += 1
    print('beads dissolved', nd)
    return lab

if __name__ == '__main__':
    base = sys.argv[1]
    lab4, band4 = run(base)
    lab4 = cleanup(lab4, band4)
    lab4 = min_width(lab4)
    lab4 = dissolve_beads(lab4)
    lab4 = cleanup(lab4, np.ones_like(band4), iters=1)
    np.save(base + '_reg4.npy', lab4.astype(np.int16))
