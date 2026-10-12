"""Outline wobble per shape: resample outline at 0.1 units, compare with a Gaussian-smoothed copy (sigma 0.7 units).
Reports the mean deviation (design units) on non-corner stretches."""
import sys, numpy as np
from scipy import ndimage as ndi
from pbart import load
def dense(sub, h=0.1):
    pts = [np.asarray(sub[0], float)]
    cur = pts[0]
    for g in sub[1:]:
        if g[0] == 'L':
            p = np.asarray(g[1], float); n = max(2, int(np.hypot(*(p - cur)) / 0.05))
            t = np.linspace(0, 1, n)[1:, None]; pts.extend(cur + (p - cur) * t); cur = p
        else:
            c1, c2, p = (np.asarray(v, float) for v in g[1:])
            n = max(4, int((np.hypot(*(c1 - cur)) + np.hypot(*(c2 - c1)) + np.hypot(*(p - c2))) / 0.05))
            t = np.linspace(0, 1, n)[1:, None]; mt = 1 - t
            pts.extend(mt ** 3 * cur + 3 * mt * mt * t * c1 + 3 * mt * t * t * c2 + t ** 3 * p); cur = p
    P = np.array(pts)
    if np.hypot(*(P[-1] - P[0])) > 1e-6: P = np.vstack([P, P[:1]])
    d = np.hypot(*np.diff(P, axis=0).T); s = np.concatenate([[0], np.cumsum(d)]); L = s[-1]
    if L < 4 * h: return None, L
    m = int(L / h); u = np.linspace(0, L, m, endpoint=False)
    Q = np.c_[np.interp(u, s, P[:, 0]), np.interp(u, s, P[:, 1])]
    return Q, L
def turn(Q, k):
    a = Q - np.roll(Q, k, 0); b = np.roll(Q, -k, 0) - Q
    return np.abs(np.angle((a[:, 0] + 1j * a[:, 1]) * np.conj(b[:, 0] + 1j * b[:, 1])))
def wobble(s, h=0.1, sig=0.7):
    devs = []; L_all = 0
    for sub in s.subs:
        Q, L = dense(sub, h)
        if Q is None: continue
        S = np.c_[ndi.gaussian_filter1d(Q[:, 0], sig / h, mode='wrap'), ndi.gaussian_filter1d(Q[:, 1], sig / h, mode='wrap')]
        t10 = turn(Q, int(1.0 / h)); t03 = turn(Q, int(0.3 / h))
        corner = (t10 > np.radians(45)) & (t03 > 0.6 * t10)
        corner = ndi.binary_dilation(corner, iterations=int(1.0 / h))
        dev = np.hypot(*(Q - S).T)[~corner]
        devs.append(dev); L_all += L
    if not devs: return 0, 0
    dv = np.concatenate(devs)
    return (dv.mean() if len(dv) else 0), L_all
if __name__ == '__main__':
    sh = load(sys.argv[1])
    W = np.array([wobble(s) for s in sh])
    np.save(sys.argv[2], W)
    for thr in (0.05, 0.08, 0.12, 0.2):
        print('mean deviation > %.2f units: %d shapes (outline length %.0f units)' % (thr, (W[:, 0] > thr).sum(), W[W[:, 0] > thr, 1].sum()))
    print('total outline length %.0f units, median dev %.3f' % (W[:, 1].sum(), np.median(W[:, 0])))
