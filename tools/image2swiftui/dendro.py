"""Layer-constrained SSE merge recorded as a dendrogram, so any region count can be cut cheaply."""
import heapq
import numpy as np
from regions import region_stats, sse, adjacency


def dendrogram(labels, img4, groups):
    """Merges adjacent regions of the same layer, cheapest first. Returns [(a, b, group, cost), ...]."""
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
    alive = [V[i][0] > 0 for i in range(n)]
    ver = [0] * n

    def add(v, w):
        return tuple(v[i] + w[i] for i in range(10))

    heap = []

    def push(a, b):
        e = sse(add(V[a], V[b])) - E[a] - E[b]
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
