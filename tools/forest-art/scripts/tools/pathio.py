"""Write subpaths back to the compact data format (absolute M, relative c/l, Z), drift-free rounding."""
import numpy as np
from art import parse_path, LAYERS

def fmt(v):
    s = '%d' % v if v % 10 == 0 else '%.1f' % (v / 10)
    if v % 10 == 0: s = '%d' % (v // 10)
    return s

def q(p):  # absolute point -> integer tenths
    return np.round(np.asarray(p) * 10).astype(np.int64)

def path_str(subs):
    out = []
    for seg in subs:
        cur = q(seg[0]); start = cur
        out.append('M%s %s' % (fmt(cur[0]), fmt(cur[1])))
        for s in seg[1:]:
            if s[0] == 'L':
                p = q(s[1]); d = p - cur
                out.append('l%s %s' % (fmt(d[0]), fmt(d[1]))); cur = p
            else:
                c1, c2, p = q(s[1]), q(s[2]), q(s[3])
                out.append('c%s %s %s %s %s %s' % tuple(fmt(v) for v in np.concatenate([c1 - cur, c2 - cur, p - cur])))
                cur = p
        out.append('Z')
    return ''.join(out).replace('lZ', 'Z')

def map_subs(subs, fn):
    res = []
    for seg in subs:
        ns = [fn(seg[0])]
        for s in seg[1:]:
            ns.append((s[0],) + tuple(fn(p) for p in s[1:]))
        res.append(ns)
    return res
