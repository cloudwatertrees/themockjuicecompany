"""Phase B: corner-preserving outline smoothing of traced shapes (removes label-map wobble, keeps corners).
Each subpath is resampled at H units, split at corners, smoothed with a shrink-compensated Gaussian
(2G - G*G, sigma SIG), displacement limited to MAXD, then refit with cubic Beziers (tolerance TOL)."""
import os, sys, json, numpy as np
from scipy import ndimage as ndi
H = 0.1; SIG = float(os.environ.get('PB_SMOOTH_SIG', '0.6')); MAXD = float(os.environ.get('PB_SMOOTH_MAXD', '0.35')); TOL = 0.03

def dense(sub):
    pts = [np.asarray(sub[0], float)]; cur = pts[0]
    for g in sub[1:]:
        if g[0] == 'L':
            p = np.asarray(g[1], float); n = max(2, int(np.hypot(*(p - cur)) / 0.02))
            t = np.linspace(0, 1, n)[1:, None]; pts.extend(cur + (p - cur) * t); cur = p
        else:
            c1, c2, p = (np.asarray(v, float) for v in g[1:])
            n = max(4, int((np.hypot(*(c1 - cur)) + np.hypot(*(c2 - c1)) + np.hypot(*(p - c2))) / 0.02))
            t = np.linspace(0, 1, n)[1:, None]; mt = 1 - t
            pts.extend(mt ** 3 * cur + 3 * mt * mt * t * c1 + 3 * mt * t * t * c2 + t ** 3 * p); cur = p
    P = np.array(pts)
    if np.hypot(*(P[-1] - P[0])) > 1e-9: P = np.vstack([P, P[:1]])
    d = np.hypot(*np.diff(P, axis=0).T); s = np.concatenate([[0], np.cumsum(d)]); L = s[-1]
    m = max(int(round(L / H)), 3); u = np.linspace(0, L, m, endpoint=False)
    return np.c_[np.interp(u, s, P[:, 0]), np.interp(u, s, P[:, 1])], L

def turn(Q, k):
    a = Q - np.roll(Q, k, 0); b = np.roll(Q, -k, 0) - Q
    return np.abs(np.angle((a[:, 0] + 1j * a[:, 1]) * np.conj(b[:, 0] + 1j * b[:, 1])))

def find_corners(Q):
    n = len(Q); k1 = max(int(1.0 / H), 1); k3 = max(int(0.3 / H), 1)
    if n < 4 * k1: return []
    t10, t03 = turn(Q, k1), turn(Q, k3)
    cand = (t10 > np.radians(45)) & (t03 > 0.6 * t10)
    out = []
    for i in np.nonzero(cand)[0]:
        w = [(i + j) % n for j in range(-k1, k1 + 1)]
        if t03[i] >= t03[w].max() - 1e-12 and all(abs(i - c) > k1 for c in out): out.append(int(i))
    return sorted(out)

def smooth_open(R):
    """Run with fixed end points (corners): odd reflection at both ends, shrink-compensated Gaussian."""
    n = len(R); s = SIG / H; pad = min(int(4 * s) + 1, n - 1)
    if n < 5: return R.copy()
    left = 2 * R[0] - R[pad:0:-1]; right = 2 * R[-1] - R[-2:-pad - 2:-1]
    X = np.vstack([left, R, right])
    g = lambda A: ndi.gaussian_filter1d(A, s, axis=0, mode='nearest')
    G = g(X); S = (2 * G - g(G))[pad:pad + n]
    D = S - R
    ramp = np.minimum(np.arange(n), np.arange(n)[::-1]) * H / (2 * SIG); D *= np.clip(ramp, 0, 1)[:, None]
    return R + limit(D)

def smooth_closed(Q):
    s = SIG / H
    g = lambda A: ndi.gaussian_filter1d(A, s, axis=0, mode='wrap')
    G = g(Q); return Q + limit(2 * G - g(G) - Q)

def limit(D):
    m = np.hypot(*D.T); f = np.minimum(1, MAXD / np.maximum(m, 1e-12)); return D * f[:, None]

# --- cubic Bezier fitting (Schneider) ---
def bez(b, t):
    t = t[:, None]; mt = 1 - t
    return mt ** 3 * b[0] + 3 * mt * mt * t * b[1] + 3 * mt * t * t * b[2] + t ** 3 * b[3]
def bez1(b, t):
    t = t[:, None]; mt = 1 - t
    return 3 * mt * mt * (b[1] - b[0]) + 6 * mt * t * (b[2] - b[1]) + 3 * t * t * (b[3] - b[2])
def bez2(b, t):
    t = t[:, None]
    return 6 * (1 - t) * (b[2] - 2 * b[1] + b[0]) + 6 * t * (b[3] - 2 * b[2] + b[1])
def gen(P, u, tl, tr):
    p0, p3 = P[0], P[-1]
    A1 = tl[None] * (3 * (1 - u) ** 2 * u)[:, None]; A2 = tr[None] * (3 * (1 - u) * u ** 2)[:, None]
    C = np.array([[np.sum(A1 * A1), np.sum(A1 * A2)], [np.sum(A1 * A2), np.sum(A2 * A2)]])
    base = bez(np.array([p0, p0, p3, p3]), u); Xv = P - base
    X = np.array([np.sum(A1 * Xv), np.sum(A2 * Xv)])
    det = C[0, 0] * C[1, 1] - C[0, 1] ** 2
    seg = np.hypot(*(p3 - p0))
    if abs(det) > 1e-12:
        al = (X[0] * C[1, 1] - X[1] * C[0, 1]) / det; ar = (C[0, 0] * X[1] - C[0, 1] * X[0]) / det
    else:
        al = ar = seg / 3
    if al < 1e-6 * seg or ar < 1e-6 * seg: al = ar = seg / 3
    return np.array([p0, p0 + tl * al, p3 + tr * ar, p3])
def reparam(b, P, u):
    d = bez(b, u) - P; d1 = bez1(b, u); d2 = bez2(b, u)
    num = np.sum(d * d1, 1); den = np.sum(d1 * d1, 1) + np.sum(d * d2, 1)
    with np.errstate(divide='ignore', invalid='ignore'):
        nu = np.where(np.abs(den) > 1e-12, u - num / den, u)
    return np.clip(nu, 0, 1)
def chord(P):
    d = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))]); return d / max(d[-1], 1e-12)
def unit(v):
    n = np.hypot(*v); return v / n if n > 1e-12 else np.array([1.0, 0.0])
def fit(P, tl, tr, depth=0):
    if len(P) == 2:
        dist = np.hypot(*(P[1] - P[0])) / 3; return [np.array([P[0], P[0] + tl * dist, P[1] + tr * dist, P[1]])]
    u = chord(P); b = gen(P, u, tl, tr)
    err = np.hypot(*(bez(b, u) - P).T); i = int(np.argmax(err))
    if err[i] < TOL: return [b]
    if err[i] < 4 * TOL:
        for _ in range(6):
            u = reparam(b, P, u); b = gen(P, u, tl, tr); err = np.hypot(*(bez(b, u) - P).T); i = int(np.argmax(err))
            if err[i] < TOL: return [b]
    i = min(max(i, 1), len(P) - 2)
    tc = unit(P[i - 1] - P[i + 1])
    return fit(P[:i + 1], tl, tc, depth + 1) + fit(P[i:], -tc, tr, depth + 1)

def smooth_sub(sub):
    Q, L = dense(sub)
    if L < 6 * SIG or len(Q) < 12: return sub                 # tiny loops: keep (dots, specks)
    cs = find_corners(Q)
    pieces = []
    if not cs:
        S = smooth_closed(Q); n = len(S); h = n // 2
        loop = np.vstack([S, S[:1]])
        t0 = unit(S[1] - S[-1]); th = unit(S[h + 1] - S[h - 1])
        pieces += fit(loop[:h + 1], t0, -th) + fit(loop[h:], th, -t0)
    else:
        n = len(Q)
        for a, c in zip(cs, cs[1:] + [cs[0] + n]):
            idx = np.arange(a, c + 1) % n; R = smooth_open(Q[idx])
            k = min(3, len(R) - 1)
            pieces += fit(R, unit(R[k] - R[0]), unit(R[-1 - k] - R[-1]))
    start = pieces[0][0]
    return [start] + [('C', b[1], b[2], b[3]) for b in pieces]

def smooth_path(subs):
    return [smooth_sub(s) for s in subs]

if __name__ == '__main__':
    from art import parse_path
    from pathio import path_str
    src, out = sys.argv[1], sys.argv[2]
    shapes = json.load(open(src)); n0 = n1 = 0
    for k, s in enumerate(shapes):
        subs = parse_path(s['path']); n0 += sum(len(u) - 1 for u in subs)
        sm = smooth_path(subs); n1 += sum(len(u) - 1 for u in sm)
        s['path'] = path_str(sm)
        if k % 500 == 0: print(k, '/', len(shapes), flush=True)
    json.dump(shapes, open(out, 'w'))
    print('smoothed %d shapes, segments %d -> %d' % (len(shapes), n0, n1))
