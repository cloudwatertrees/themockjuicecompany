import os
"""Phase B stage 4: draw order, blur assignment, stacked masks at 4x, potrace -> shape list."""
import sys, json, numpy as np
from scipy import ndimage as ndi
from scipy.special import erf
from scipy.optimize import brentq
from art import W, H, LAYERS
from trace import trace
from pathio import path_str
SP = '/Users/laverath/Desktop/themockjuicecompany/tools/scene-trace/work/'
U = 4
HARD, SOFT, SMOOTH = 0, 1, 2

def sigma_from_ratio(r):
    """Gaussian edge sigma (px) from near/mid contrast ratio (spans +-1.5 and +-3.5 px)."""
    f = lambda s: erf(1.5 / (np.sqrt(2) * s)) / erf(3.5 / (np.sqrt(2) * s)) - r
    try: return brentq(f, 0.2, 20)
    except ValueError: return 0.2 if r > 0.9 else 20

def plan(base, soft_frac=0.6, psf=0.38):
    reg = np.load(base + '_reg.npy'); lay = np.load(base + '_layer.npy'); P = np.load(base + '_pairs.npy')
    n = reg.max() + 1
    area = np.bincount(reg.ravel(), minlength=n)
    blen = np.zeros(n); soft_len = np.zeros(n); sig_acc = [[] for _ in range(n)]
    nb_hard = [set() for _ in range(n)]; nb_soft = [set() for _ in range(n)]
    for a, b, c, cnt, near, mid, far in P:
        a, b, c = int(a), int(b), int(c)
        blen[a] += cnt; blen[b] += cnt
        if c == HARD: nb_hard[a].add(b); nb_hard[b].add(a)
        if c == SOFT:
            small = a if area[a] < area[b] else b
            soft_len[small] += cnt
            s = sigma_from_ratio(near / max(mid, 1e-6))
            sig_acc[small].append((s, cnt))
            nb_soft[small].add(a + b - small)
    blur = np.zeros(n)
    for r in range(n):
        if blen[r] > 0 and soft_len[r] / blen[r] >= soft_frac and sig_acc[r]:
            s = np.array(sig_acc[r]); se = np.average(s[:, 0], weights=s[:, 1])
            sb = np.sqrt(max(se ** 2 - psf ** 2, 0))
            blur[r] = min(max(sb, 0.8), 8.0)
    # order: layer, then constraints (blurred after soft base, hard neighbours of blurred after it), area desc
    key = np.zeros(n)
    rank_in_layer = np.argsort(np.argsort(-area))          # big first
    key = lay.astype(float) * 1e7 + rank_in_layer
    # one relaxation pass: blurred region just after its largest soft base; its hard same-layer neighbours after it
    for r in np.nonzero(blur > 0)[0]:
        bases = [b for b in nb_soft[r] if lay[b] == lay[r]]
        if bases: key[r] = max(key[r], max(key[b] for b in bases) + 0.5)
        for h in nb_hard[r]:
            if lay[h] == lay[r] and key[h] <= key[r]: key[h] = key[r] + 0.25
    # drop blur where a hard neighbour is drawn earlier (its edge would be softened)
    dropped = 0
    for r in np.nonzero(blur > 0)[0]:
        if any(key[h] < key[r] for h in nb_hard[r]):
            hard_len = sum(1 for h in nb_hard[r] if key[h] < key[r])
            blur[r] = 0; dropped += 1
    order = np.argsort(key, kind='stable')
    print('regions %d, blurred %d (dropped %d), blur sigma median %.2f' % (n, (blur > 0).sum(), dropped, np.median(blur[blur > 0]) if (blur > 0).any() else 0))
    return order, blur, lay

def run(base, out):
    reg4 = np.load(base + '_reg4.npy')
    from pb_soft import plan as plan2
    from PIL import Image
    from skimage.color import rgb2lab
    reg = np.load(base + '_reg.npy'); lay = np.load(base + '_layer.npy'); P = np.load(base + '_pairs.npy')
    rl = rgb2lab(np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255)
    import os
    order, blur = plan2(reg, lay, P, rl, enable=os.environ.get('PB_BLUR', '1') == '1')
    rank = np.empty(len(order), int); rank[order] = np.arange(len(order)); np.save(base + '_rank.npy', rank)
    if os.environ.get('PB_RIMS', '0') == '1':
        import json as _j
        reg4 = np.load(base + '_reg4r.npy'); rims = _j.load(open(base + '_rims.json'))
        after = {}
        for rid, F in rims: after.setdefault(F, []).append(rid)
        n0 = len(lay); nr = reg4.max() + 1
        lay = np.concatenate([lay, np.zeros(nr - n0, lay.dtype)]); blur = np.concatenate([blur, np.zeros(nr - n0)])
        for rid, F in rims: lay[rid] = lay[F]
        order = np.array([v for r in order for v in [r] + after.get(int(r), [])])
    n = len(order); pos = np.empty(n, int); pos[order] = np.arange(n)
    rank4 = pos.astype(np.int32)[reg4]                 # draw rank per 4x pixel
    objs = ndi.find_objects(reg4.astype(np.int32) + 1, max_label=int(max(reg4.max() + 1, len(order))))
    shapes = []
    for k, r in enumerate(order):
        sl = objs[r]
        if sl is None: continue
        y0, y1 = max(sl[0].start - 10, 0), min(sl[0].stop + 10, H * U); x0, x1 = max(sl[1].start - 10, 0), min(sl[1].stop + 10, W * U)
        m = reg4[y0:y1, x0:x1] == r
        later = rank4[y0:y1, x0:x1] > k
        holes = ndi.binary_fill_holes(m) & ~m & later
        ext = ndi.binary_dilation(m, iterations=6) & later
        full = m | holes | ext
        comps, nc = ndi.label(full)
        for ci in range(1, nc + 1):
            mask = comps == ci
            if (mask & m).sum() < 2: continue
            shapes_add(shapes, mask, x0, y0, x1, y1, r, lay, blur)
        if k % 500 == 0: print(k, '/', n)
    json.dump(shapes, open(out, 'w'))
    print('traced', len(shapes))

def shapes_add(shapes, mask, x0, y0, x1, y1, r, lay, blur):
    # extend off-canvas where the region touches the canvas edge
    pt = 16 if y0 == 0 and mask[0].any() else 0; pb = 16 if y1 == H * U and mask[-1].any() else 0
    pl = 16 if x0 == 0 and mask[:, 0].any() else 0; pr = 16 if x1 == W * U and mask[:, -1].any() else 0
    mask = np.pad(mask, ((pt, pb), (pl, pr)), mode='edge')
    mask = np.pad(mask, 4)
    sig = float(os.environ.get('PB_SDF', '0'))
    if sig > 0:
        # smooth the outline: Gaussian-smoothed signed distance (float32, clipped to the boundary band), zero
        # level traced at 2x the label resolution; thin masks (rims) get proportionally smaller smoothing
        inside = ndi.distance_transform_edt(mask).astype(np.float32)
        sg = min(sig, max(0.5, float(inside.max()) / 3.0))
        sdf = np.clip(inside - ndi.distance_transform_edt(~mask).astype(np.float32), -8, 8)
        del inside
        sdf = ndi.gaussian_filter(sdf, sg, output=np.float32)
        hi = np.zeros((sdf.shape[0] * 2, sdf.shape[1] * 2), bool)
        for r0 in range(0, sdf.shape[0], 256):
            a0, a1 = max(r0 - 2, 0), min(r0 + 258, sdf.shape[0])
            z = ndi.zoom(sdf[a0:a1], 2, order=1, grid_mode=True, mode='nearest') > 0
            hi[2 * r0:2 * min(r0 + 256, sdf.shape[0])] = z[2 * (r0 - a0):2 * (r0 - a0) + 2 * (min(r0 + 256, sdf.shape[0]) - r0)]
        del sdf
        subs = trace(hi, 2 * U, (x0 - pl - 4) / U, (y0 - pt - 4) / U, turd=4, alphamax=1.0, opt=float(os.environ.get('PB_OPT', '0.4')))
    else:
        subs = trace(mask, U, (x0 - pl - 4) / U, (y0 - pt - 4) / U, turd=2, alphamax=1.0, opt=float(os.environ.get('PB_OPT', '0.4')))
    if not subs: return
    shapes.append({'region': int(r), 'layer': LAYERS[lay[r]], 'blur': float(blur[r]), 'path': path_str(subs)})

if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
