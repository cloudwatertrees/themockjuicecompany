"""Schneider-style cubic Bezier fitting with per-point tolerance and corner detection."""
import numpy as np


def _bez(b, t):
    t = t[:, None]
    mt = 1 - t
    return mt**3 * b[0] + 3 * mt**2 * t * b[1] + 3 * mt * t**2 * b[2] + t**3 * b[3]


def _bez_d1(b, t):
    t = t[:, None]
    mt = 1 - t
    return 3 * mt**2 * (b[1] - b[0]) + 6 * mt * t * (b[2] - b[1]) + 3 * t**2 * (b[3] - b[2])


def _bez_d2(b, t):
    t = t[:, None]
    mt = 1 - t
    return 6 * mt * (b[2] - 2 * b[1] + b[0]) + 6 * t * (b[3] - 2 * b[2] + b[1])


def _chord_u(p):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    return d / d[-1] if d[-1] > 0 else np.linspace(0, 1, len(p))


def _generate(p, u, t1, t2):
    p0, p3 = p[0], p[-1]
    mt = 1 - u
    b0 = mt**3
    b1 = 3 * mt**2 * u
    b2 = 3 * mt * u**2
    b3 = u**3
    A1 = t1[None] * b1[:, None]
    A2 = t2[None] * b2[:, None]
    C = np.array([[np.sum(A1 * A1), np.sum(A1 * A2)], [0, np.sum(A2 * A2)]])
    C[1, 0] = C[0, 1]
    tmp = p - (p0 * (b0 + b1)[:, None] + p3 * (b2 + b3)[:, None])
    X = np.array([np.sum(A1 * tmp), np.sum(A2 * tmp)])
    det = C[0, 0] * C[1, 1] - C[0, 1] ** 2
    seg = np.linalg.norm(p3 - p0)
    if abs(det) > 1e-12:
        a1 = (X[0] * C[1, 1] - X[1] * C[0, 1]) / det
        a2 = (C[0, 0] * X[1] - C[0, 1] * X[0]) / det
    else:
        a1 = a2 = seg / 3
    eps = 1e-6 * seg
    if a1 < eps or a2 < eps or a1 > 2 * seg or a2 > 2 * seg:
        a1 = a2 = seg / 3
    return np.array([p0, p0 + t1 * a1, p3 + t2 * a2, p3])


def _reparam(b, p, u):
    d = _bez(b, u) - p
    d1 = _bez_d1(b, u)
    d2 = _bez_d2(b, u)
    num = np.sum(d * d1, 1)
    den = np.sum(d1 * d1, 1) + np.sum(d * d2, 1)
    with np.errstate(divide='ignore', invalid='ignore'):
        nu = np.where(np.abs(den) > 1e-12, u - num / den, u)
    nu = np.clip(nu, 0, 1)
    nu[0], nu[-1] = 0, 1
    return np.maximum.accumulate(nu)


def _maxerr(b, p, u, tol):
    e = np.linalg.norm(_bez(b, u) - p, axis=1) / tol
    i = int(np.argmax(e[1:-1])) + 1 if len(p) > 2 else len(p) // 2
    return e.max(), i


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def fit_open(p, tol, t1, t2, depth=0):
    n = len(p)
    if n <= 2 or np.linalg.norm(p[-1] - p[0]) < 1e-9 and n <= 3:
        d = np.linalg.norm(p[-1] - p[0]) / 3
        return [np.array([p[0], p[0] + t1 * d, p[-1] + t2 * d, p[-1]])]
    u = _chord_u(p)
    b = _generate(p, u, t1, t2)
    err, split = _maxerr(b, p, u, tol)
    if err <= 1:
        return [b]
    if err <= 6:
        for _ in range(12):
            u = _reparam(b, p, u)
            b = _generate(p, u, t1, t2)
            err, split = _maxerr(b, p, u, tol)
            if err <= 1:
                return [b]
    if n < 4 or depth > 40:
        return [b]
    split = min(max(split, 1), n - 2)
    tc = _unit(p[split - 1] - p[split + 1])
    if np.linalg.norm(tc) < 1e-9:
        tc = _unit(p[split - 1] - p[split])
    return fit_open(p[:split + 1], tol[:split + 1], t1, tc, depth + 1) + \
        fit_open(p[split:], tol[split:], -tc, t2, depth + 1)


def _end_tangent(p, k=4):
    """Unit tangent leaving p[0] into the curve, from a short least-squares chord."""
    m = min(len(p) - 1, k)
    v = p[1:m + 1] - p[0]
    w = np.linspace(1, 0.5, m)[:, None]
    return _unit((v * w).sum(0))


def corners(p, r=3.0, ang=55):
    """Indices of corner vertices on closed polyline p using chords of arc length r."""
    n = len(p)
    if n < 8:
        return []
    seg = np.linalg.norm(np.roll(p, -1, 0) - p, axis=1)
    s = np.r_[0, np.cumsum(seg)]
    L = s[-1]
    s = s[:-1]

    def at(t):
        t = np.mod(t, L)
        j = np.searchsorted(s, t, side='right') - 1
        f = (t - s[j]) / np.maximum(seg[j], 1e-9)
        return p[j] + (p[(j + 1) % n] - p[j]) * f[:, None]

    a = at(s - r)
    b = at(s + r)
    v1 = p - a
    v2 = b - p
    c = np.sum(v1 * v2, 1) / (np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1) + 1e-12)
    turn = np.degrees(np.arccos(np.clip(c, -1, 1)))
    cand = []
    for i in np.argsort(-turn):
        if turn[i] < ang:
            break
        if all(min(abs(s[i] - s[j]), L - abs(s[i] - s[j])) > r for j in cand):
            cand.append(i)
    return sorted(cand)


def fit_closed(p, tol, r=3.0, ang=55):
    """Fit a closed polyline (no repeated endpoint). Returns list of 4x2 cubic segments."""
    n = len(p)
    cs = corners(p, r, ang)
    if not cs:
        # smooth closed curve: start at an arbitrary vertex, shared tangent at the join
        i0 = 0
        q = np.vstack([p[i0:], p[:i0 + 1]])
        tq = np.r_[tol[i0:], tol[:i0 + 1]]
        t = _unit(p[(i0 + 1) % n] - p[(i0 - 1) % n])
        if n < 6:
            return fit_open(q, tq, t, -t)
        # split in two halves to give the fitter room
        h = len(q) // 2
        th = _unit(q[h + 1] - q[h - 1])
        return fit_open(q[:h + 1], tq[:h + 1], t, -th) + fit_open(q[h:], tq[h:], th, -t)
    segs = []
    for k in range(len(cs)):
        a = cs[k]
        b = cs[(k + 1) % len(cs)]
        idx = np.arange(a, b + 1) if b > a else np.r_[np.arange(a, n), np.arange(0, b + 1)]
        q = p[idx]
        tq = tol[idx]
        if len(q) < 2:
            continue
        t1 = _end_tangent(q)
        t2 = _end_tangent(q[::-1])
        segs += fit_open(q, tq, t1, t2)
    return segs


def _sample(b, n=12):
    t = np.linspace(0, 1, n)
    return _bez(b, t)


def _is_smooth_join(b1, b2, max_deg=20):
    t1 = b1[3] - b1[2]
    t2 = b2[1] - b2[0]
    n1, n2 = np.linalg.norm(t1), np.linalg.norm(t2)
    if n1 < 1e-9 or n2 < 1e-9:
        return False
    return np.degrees(np.arccos(np.clip(np.dot(t1, t2) / (n1 * n2), -1, 1))) < max_deg


def merge_segments(segs, tol, closed=True):
    """Greedily replace pairs of consecutive smooth-joined cubics by one cubic within tol."""
    segs = [np.asarray(s, float) for s in segs]
    changed = True
    while changed and len(segs) > 2:
        changed = False
        i = 0
        while i < (len(segs) if closed else len(segs) - 1) and len(segs) > 2:
            j = (i + 1) % len(segs)
            b1, b2 = segs[i], segs[j]
            if _is_smooth_join(b1, b2):
                p = np.vstack([_sample(b1)[:-1], _sample(b2)])
                t1 = _unit(b1[1] - b1[0]) if np.linalg.norm(b1[1] - b1[0]) > 1e-9 else _unit(p[1] - p[0])
                t2 = _unit(b2[2] - b2[3]) if np.linalg.norm(b2[2] - b2[3]) > 1e-9 else _unit(p[-2] - p[-1])
                u = _chord_u(p)
                b = _generate(p, u, t1, t2)
                for _ in range(8):
                    u = _reparam(b, p, u)
                    b = _generate(p, u, t1, t2)
                err = np.linalg.norm(_bez(b, u) - p, axis=1).max()
                if err <= tol:
                    segs[i] = b
                    del segs[j]
                    if j < i:
                        i -= 1
                    changed = True
                    continue
            i += 1
    return segs
