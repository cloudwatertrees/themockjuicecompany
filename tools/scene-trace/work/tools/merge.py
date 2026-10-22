"""Greedy region merging with a smooth colour model (polynomial in x,y fitted in Lab) via moment sums.
Merge cost = increase in squared residual; same-layer only."""
import sys, heapq, numpy as np
from PIL import Image
from skimage.color import rgb2lab
from art import load, LAYERS, W, H
SP = '/Users/laverath/Desktop/themockjuicecompany/tools/scene-trace/work/'

def basis(xs, ys, deg):
    x, y = xs / 100.0, ys / 100.0
    cols = [np.ones_like(x)]
    for d in range(1, deg + 1):
        for i in range(d + 1):
            cols.append(x ** (d - i) * y ** i)
    return np.stack(cols, -1)

class Stats:
    """Per-region moments: n, A = sum phi phi^T, B = sum phi c^T, C = sum |c|^2, centred per region on demand."""
    def __init__(s, lab, ref_lab, deg):
        s.deg = deg
        ys, xs = np.mgrid[0:H, 0:W]
        Phi = basis(xs.ravel() + 0.5, ys.ravel() + 0.5, deg); C = ref_lab.reshape(-1, 3); L = lab.ravel()
        k = Phi.shape[1]; n = L.max() + 1
        s.n = np.bincount(L, minlength=n).astype(float)
        s.A = np.zeros((n, k, k)); s.B = np.zeros((n, k, 3)); s.C = np.zeros(n)
        for i in range(k):
            for j in range(i, k):
                v = np.bincount(L, Phi[:, i] * Phi[:, j], minlength=n); s.A[:, i, j] = v; s.A[:, j, i] = v
            for c in range(3):
                s.B[:, i, c] = np.bincount(L, Phi[:, i] * C[:, c], minlength=n)
        s.C = np.bincount(L, (C ** 2).sum(1), minlength=n)
        s.k = k
    def sse(s, A, B, C, n):
        if n < 1: return 0.0
        R = np.eye(s.k) * 1e-3 * n; R[0, 0] = 0
        X = np.linalg.solve(A + R, B)
        return max(C - (B * X).sum(), 0.0)

def merge(lab, layer_of, ref_lab, deg=3, tau=6.0, min_tau_small=None):
    st = Stats(lab, ref_lab, deg)
    n = len(st.n)
    sse = np.array([st.sse(st.A[i], st.B[i], st.C[i], st.n[i]) for i in range(n)])
    # adjacency
    a = np.concatenate([lab[:, :-1].ravel(), lab[:-1].ravel()]); b = np.concatenate([lab[:, 1:].ravel(), lab[1:].ravel()])
    m = a != b; a, b = np.minimum(a[m], b[m]), np.maximum(a[m], b[m])
    pairs = np.unique(a.astype(np.int64) * n + b)
    nb = [set() for _ in range(n)]
    for p in pairs:
        i, j = int(p // n), int(p % n)
        if layer_of[i] == layer_of[j]: nb[i].add(j); nb[j].add(i)
    alive = np.ones(n, bool); parent = np.arange(n); ver = np.zeros(n, int)
    def cost(i, j):
        A = st.A[i] + st.A[j]; B = st.B[i] + st.B[j]; C = st.C[i] + st.C[j]; nn = st.n[i] + st.n[j]
        s = st.sse(A, B, C, nn)
        return (s - sse[i] - sse[j]) / max(min(st.n[i], st.n[j]), 1.0), s
    heap = []
    for i in range(n):
        for j in nb[i]:
            if i < j:
                c, _ = cost(i, j); heap.append((c, i, j, 0, 0))
    heapq.heapify(heap)
    while heap:
        c, i, j, vi, vj = heapq.heappop(heap)
        if c > tau: break
        if not (alive[i] and alive[j]) or vi != ver[i] or vj != ver[j]: continue
        c2, s = cost(i, j)
        # merge j into i
        st.A[i] += st.A[j]; st.B[i] += st.B[j]; st.C[i] += st.C[j]; st.n[i] += st.n[j]; sse[i] = s
        alive[j] = False; parent[j] = i; ver[i] += 1
        nb[i] |= nb[j]; nb[i].discard(i); nb[i].discard(j)
        for k in nb[j]:
            nb[k].discard(j)
            if k != i: nb[k].add(i)
        nb[j] = set()
        for k in nb[i]:
            cc, _ = cost(i, k)
            a_, b_ = (i, k) if i < k else (k, i)
            heapq.heappush(heap, (cc, a_, b_, ver[a_], ver[b_]))
    def root(x):
        while parent[x] != x: x = parent[x]
        return x
    roots = np.array([root(x) for x in range(n)])
    return roots, st, sse

if __name__ == '__main__':
    src, deg, tau = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
    shapes = load(src); layer_of = np.array([LAYERS.index(s.layer) for s in shapes])
    lab = np.load(SP + 'out/B_shapelab.npy')
    ul, inv = np.unique(lab, return_inverse=True); inv = inv.reshape(lab.shape)
    ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
    roots, st, sse = merge(inv, layer_of[ul], rgb2lab(ref), deg, tau)
    reg = roots[inv]
    ur, reg = np.unique(reg, return_inverse=True); reg = reg.reshape(lab.shape)
    sizes = np.bincount(reg.ravel())
    rms = np.sqrt(sse[ur] / np.maximum(st.n[ur], 1))
    print('deg %d tau %.1f: regions %d, median size %.0f, <10px %d, max %d; region RMS (Lab) median %.2f p90 %.2f max %.2f' % (
        deg, tau, len(ur), np.median(sizes), (sizes < 10).sum(), sizes.max(), np.median(rms), np.percentile(rms, 90), rms.max()))
    np.save(SP + f'out/B_reg_d{deg}_t{tau:g}.npy', reg)
    np.save(SP + f'out/B_reglayer_d{deg}_t{tau:g}.npy', layer_of[ul][np.array([np.nonzero(roots == r)[0][0] for r in ur])])
