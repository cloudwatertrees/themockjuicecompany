"""Layer-constrained SSE merge recorded as a dendrogram, so any region count can be cut cheaply."""
import heapq
import numpy as np
from regions import region_stats, sse, adjacency


def boundary_contrast(labels, img):
    """Per adjacent label pair: (sum of max-channel |colour difference| across the shared boundary, pixel-pair count),
    measured on the source pixels on either side."""
    out = {}
    for la, lb, ca, cb in [(labels[:, :-1], labels[:, 1:], img[:, :-1], img[:, 1:]),
                           (labels[:-1], labels[1:], img[:-1], img[1:])]:
        m = la != lb
        a, b = la[m], lb[m]
        d = np.abs(ca[m] - cb[m]).max(-1)
        lo, hi = np.minimum(a, b), np.maximum(a, b)
        key = lo.astype(np.int64) * (labels.max() + 1) + hi
        u, inv = np.unique(key, return_inverse=True)
        sm = np.bincount(inv, weights=d)
        ct = np.bincount(inv).astype(float)
        n1 = labels.max() + 1
        for k, s_, c_ in zip(u, sm, ct):
            p = (int(k // n1), int(k % n1))
            o = out.get(p, (0.0, 0.0))
            out[p] = (o[0] + s_, o[1] + c_)
    return out


def dendrogram(labels, img4, groups, edge_tau=0.0, edge_power=2.0):
    """Merges adjacent regions of the same layer, cheapest first. Returns [(a, b, group, cost), ...].
    edge_tau > 0: each merge's SSE increase is multiplied by 1 + (c / edge_tau) ** edge_power, where c is the mean
    source contrast across the pair's shared boundary, so high-contrast edges (line art, outlines, spots, thin strokes)
    are merged last and survive the cut."""
    st = region_stats(labels, img4)
    n = len(st['n'])
    V = [(st['n'][i], st['sx'][i], st['sy'][i], st['sxx'][i], st['sxy'][i], st['syy'][i],
          st['sc'][i].copy(), st['scx'][i].copy(), st['scy'][i].copy(), st['scc'][i].copy()) for i in range(n)]
    E = [sse(v) for v in V]
    nb = [set() for _ in range(n)]
    for a, b in adjacency(labels):
        if groups[a] == groups[b]:
            nb[a].add(b)
            nb[b].add(a)
    BC = boundary_contrast(labels, img4[..., :3]) if edge_tau > 0 else {}
    alive = [V[i][0] > 0 for i in range(n)]
    ver = [0] * n

    def add(v, w):
        return tuple(v[i] + w[i] for i in range(10))

    heap = []

    def push(a, b):
        e = sse(add(V[a], V[b])) - E[a] - E[b]
        if edge_tau > 0:
            sm, ct = BC.get((a, b), (0.0, 0.0))
            if ct:
                e *= 1 + (sm / ct / edge_tau) ** edge_power
        heapq.heappush(heap, (e, a, b, ver[a], ver[b]))

    for a in range(n):
        for b in nb[a]:
            if a < b:
                push(a, b)
    seq = []
    while heap:
        e, a, b, va, vb = heapq.heappop(heap)
        if not (alive[a] and alive[b]) or va != ver[a] or vb != ver[b]:
            continue
        V[a] = add(V[a], V[b])
        E[a] = sse(V[a])
        alive[b] = False
        ver[a] += 1
        seq.append((a, b, groups[a], e))
        if edge_tau > 0:
            BC.pop((min(a, b), max(a, b)), None)
            for c in nb[b]:
                if c == a:
                    continue
                sb = BC.pop((min(b, c), max(b, c)), (0.0, 0.0))
                k = (min(a, c), max(a, c))
                o = BC.get(k, (0.0, 0.0))
                BC[k] = (o[0] + sb[0], o[1] + sb[1])
        nb[a] |= nb[b]
        nb[a].discard(a)
        nb[a].discard(b)
        for c in nb[b]:
            if c != a:
                nb[c].discard(b)
                nb[c].add(a)
        nb[b] = set()
        for c in nb[a]:
            push(min(a, c), max(a, c))
    return seq


def global_cut(fine, groups, seq, N):
    """Replays the cheapest merges until N regions remain. Returns (labels, layer of each label)."""
    n = fine.max() + 1
    parent = np.arange(n)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b, g, e in seq[:max(n - N, 0)]:
        parent[find(b)] = find(a)
    root = np.array([find(i) for i in range(n)])
    lab = root[fine]
    u, lab = np.unique(lab, return_inverse=True)
    return lab.reshape(fine.shape), np.asarray(groups)[u]
