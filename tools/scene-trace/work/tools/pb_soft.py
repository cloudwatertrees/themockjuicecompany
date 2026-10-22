"""Soft regions (blurred), their blur sigma from erf fits of the reference profile, and a constrained draw order."""
import heapq, numpy as np
from scipy import ndimage as ndi
from scipy.special import erf
from scipy.optimize import least_squares
from regions import boundary_pairs
from art import W, H
HARD, SOFT, SMOOTH = 0, 1, 2

def pair_profiles(reg, rl, a, b, ys0, xs0, ys1, xs1, tmax=4.0):
    """Mean oriented profile (a -> b) of the reference projected on the a->b colour axis."""
    t = np.arange(-tmax, tmax + 0.01, 0.5)
    ny, nx = ys1 - ys0, xs1 - xs0                    # unit axis from the a-pixel to the b-pixel
    cy, cx = (ys0 + ys1) / 2 + 0.5, (xs0 + xs1) / 2 + 0.5
    py = cy[:, None] + ny[:, None] * t[None]; px = cx[:, None] + nx[:, None] * t[None]
    samp = np.stack([ndi.map_coordinates(rl[..., c], [py - 0.5, px - 0.5], order=1, mode='nearest') for c in range(3)], -1)
    ca, cb = samp[:, 0].mean(0), samp[:, -1].mean(0)
    v = cb - ca; vv = v @ v
    if vv < 1e-6: return t, None
    prof = ((samp - ca) @ v / vv).mean(0)
    return t, prof

def fit_sigma(t, prof):
    def f(p):
        a, b, t0, s = p
        return a + b * 0.5 * (1 + erf((t - t0) / (np.sqrt(2) * abs(s) + 1e-6))) - prof
    r = least_squares(f, [0.0, 1.0, 0.0, 1.5], bounds=([-1, 0.2, -3, 0.2], [1, 2, 3, 10]))
    return abs(r.x[3]), np.sqrt(np.mean(r.fun ** 2))

def plan(reg, lay, P, rl, min_soft=0.4, psf=0.38, max_hard_earlier=0.1, enable=True):
    n = reg.max() + 1
    area = np.bincount(reg.ravel(), minlength=n)
    y0, x0, y1, x1 = boundary_pairs(reg)
    a_, b_ = reg[y0, x0], reg[y1, x1]
    pclass = {(int(a), int(b)): int(c) for a, b, c, *_ in P}
    blen = np.zeros(n); nbrs = [dict() for _ in range(n)]           # neighbour -> (class, length)
    for a, b, c, cnt, *_ in P:
        a, b, c = int(a), int(b), int(c)
        blen[a] += cnt; blen[b] += cnt
        nbrs[a][b] = (c, cnt); nbrs[b][a] = (c, cnt)
    # candidate soft regions: enough soft boundary with larger neighbours (their soft bases)
    soft = np.zeros(n, bool); bases = [[] for _ in range(n)]
    for r in range(n):
        sl = sum(cnt for q, (c, cnt) in nbrs[r].items() if c == SOFT and area[q] > area[r])
        if enable and blen[r] > 0 and sl / blen[r] >= min_soft:
            soft[r] = True; bases[r] = [q for q, (c, cnt) in nbrs[r].items() if c == SOFT and area[q] > area[r]]
    # sigma per soft region from its soft boundaries
    key = np.minimum(a_, b_).astype(np.int64) * n + np.maximum(a_, b_)
    order_k = np.argsort(key, kind='stable'); ks = key[order_k]
    sigma = np.zeros(n)
    for r in np.nonzero(soft)[0]:
        acc = []
        for q in bases[r]:
            k = min(r, q) * n + max(r, q)
            lo, hi = np.searchsorted(ks, k), np.searchsorted(ks, k, 'right')
            idx = order_k[lo:hi]
            if len(idx) < 4: continue
            # orient each pair from base q to region r
            sw = a_[idx] == r
            Y0 = np.where(sw, y1[idx], y0[idx]); X0 = np.where(sw, x1[idx], x0[idx])
            Y1 = np.where(sw, y0[idx], y1[idx]); X1 = np.where(sw, x0[idx], x1[idx])
            t, prof = pair_profiles(reg, rl, q, r, Y0, X0, Y1, X1)
            if prof is None: continue
            s, res = fit_sigma(t, prof)
            if res < 0.15: acc.append((s, len(idx)))
        if acc:
            s = np.average([v for v, _ in acc], weights=[w for _, w in acc])
            sigma[r] = np.sqrt(max(s ** 2 - psf ** 2 - 0.29 ** 2, 0.0))
        if sigma[r] < 0.9: soft[r] = False; sigma[r] = 0
    # thin regions (rims, lines) stay crisp
    e = np.zeros_like(reg, bool)
    e[:, 1:] |= reg[:, 1:] != reg[:, :-1]; e[:, :-1] |= reg[:, 1:] != reg[:, :-1]
    e[1:] |= reg[1:] != reg[:-1]; e[:-1] |= reg[1:] != reg[:-1]
    dt = ndi.distance_transform_edt(~e)
    thick = ndi.maximum(dt, reg, np.arange(n))
    for r in np.nonzero(soft)[0]:
        if thick[r] < max(3.0, 2.0 * sigma[r]): soft[r] = False; sigma[r] = 0
    # drop blur where hard edges with earlier layers are significant
    for r in np.nonzero(soft)[0]:
        he = sum(cnt for q, (c, cnt) in nbrs[r].items() if c == HARD and lay[q] < lay[r])
        if he / blen[r] > max_hard_earlier: soft[r] = False; sigma[r] = 0
    # quantise sigma to classes so blurred runs batch
    classes = np.array([1.0, 1.5, 2.25, 3.25, 4.5, 6.0])
    sigma[soft] = np.minimum(sigma[soft], 6.0)
    sigma[soft] = classes[np.abs(classes[None] - sigma[soft][:, None]).argmin(1)]
    # constrained order per layer: base -> soft region -> its same-layer hard neighbours; Kahn with priority
    order = []
    for L in np.unique(lay):
        nodes = np.nonzero(lay == L)[0]
        inl = set(nodes.tolist())
        succ = {v: set() for v in nodes}; indeg = {v: 0 for v in nodes}
        def add(u, v):
            if v not in succ[u]: succ[u].add(v); indeg[v] += 1
        for r in nodes:
            if not soft[r]: continue
            for q in bases[r]:
                if q in inl: add(q, r)
            for q, (c, cnt) in nbrs[r].items():
                if c == HARD and q in inl and not soft[q]: add(r, q)
        heap = [(-area[v], int(v)) for v in nodes if indeg[v] == 0]; heapq.heapify(heap)
        emitted = []; last_sigma = 0
        while heap:
            # prefer continuing a run of the same blur class
            cand = [h for h in heap if soft[h[1]] and sigma[h[1]] == last_sigma] if last_sigma else []
            if cand:
                h = min(cand); heap.remove(h); heapq.heapify(heap)
            else:
                h = heapq.heappop(heap)
            v = h[1]; emitted.append(v); last_sigma = sigma[v] if soft[v] else 0
            for w in succ[v]:
                indeg[w] -= 1
                if indeg[w] == 0: heapq.heappush(heap, (-area[w], int(w)))
        if len(emitted) < len(nodes):          # cycle: emit the rest by area, unblurred
            rest = [v for v in nodes if v not in set(emitted)]
            for v in rest: soft[v] = False; sigma[v] = 0
            emitted += sorted(rest, key=lambda v: -area[v])
        order += emitted
    order = np.array(order)
    runs = sum(1 for i in range(len(order)) if soft[order[i]] and (i == 0 or sigma[order[i - 1]] != sigma[order[i]] or lay[order[i - 1]] != lay[order[i]]))
    print('soft regions %d (sigma classes %s), blurred runs %d' % (soft.sum(), dict(zip(*np.unique(sigma[soft], return_counts=True))), runs))
    return order, np.where(soft, sigma, 0.0)
