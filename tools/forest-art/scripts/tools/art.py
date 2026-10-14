"""ForestPathArt data model: parse layer data, flatten paths, AA-rasterize, composite."""
import numpy as np, re, os

LAYERS = ['meadow', 'hedge', 'pathEdges', 'path', 'pond', 'backTrees', 'pines', 'bridge', 'bushes',
          'doorBush', 'door', 'stones', 'rocks', 'fox', 'log', 'flowers', 'frontTrees']
from PIL import Image as _Image
import os as _os
W, H = 937, 1678                                   # live art size; overridden by the reference size when a working copy has one
if _os.path.exists('/tmp/work/fv2/ref/ref.png'):  # relocate.sh rewrites this path to WORKDIR/ref/ref.png
    W, H = _Image.open('/tmp/work/fv2/ref/ref.png').size
TOK = re.compile(r'[MLCZlc]|-?\d+(?:\.\d+)?|-?\.\d+')

def hex2rgb(h):
    v = int(h, 16)
    return np.array([(v >> 16) & 255, (v >> 8) & 255, v & 255], np.float64) / 255

def rgb2hex(c):
    c = np.clip(np.round(np.asarray(c) * 255), 0, 255).astype(int)
    return '%02X%02X%02X' % tuple(c)

def parse_path(s):
    """SVG subset -> list of subpaths, each a list of segments ('L', p1) / ('C', c1, c2, p) with a start point."""
    t = TOK.findall(s)
    i = 0; subs = []; cur = np.zeros(2); start = np.zeros(2); seg = None
    def num():
        nonlocal i
        v = float(t[i]); i += 1; return v
    def pt(o):
        x = num(); y = num(); return o + np.array([x, y])
    while i < len(t):
        c = t[i]; i += 1
        if c == 'M':
            cur = pt(np.zeros(2)); start = cur.copy(); seg = [cur.copy()]; subs.append(seg)
        elif c in 'Ll':
            cur = pt(cur if c == 'l' else np.zeros(2)); seg.append(('L', cur.copy()))
        elif c in 'Cc':
            o = cur if c == 'c' else np.zeros(2)
            c1 = pt(o); c2 = pt(o); cur = pt(o); seg.append(('C', c1, c2, cur.copy()))
        elif c == 'Z':
            cur = start.copy()
        else:
            raise ValueError(c)
    return subs

class Shape:
    __slots__ = ('layer', 'idx', 'c0', 'c1', 'p0', 'p1', 'subs', 'pathstr', 'grad')
    def __init__(self, layer, idx, line):
        self.layer = layer; self.idx = idx
        toks = line.split(' ', 1)
        self.c0 = hex2rgb(toks[0]); rest = toks[1]
        if rest.startswith('M'):
            self.grad = False; self.c1 = self.c0; self.p0 = self.p1 = None
        else:
            f = rest.split(' ', 5)
            self.grad = True; self.c1 = hex2rgb(f[0])
            self.p0 = np.array([float(f[1]), float(f[2])]); self.p1 = np.array([float(f[3]), float(f[4])])
            rest = f[5]
        self.pathstr = rest
        self.subs = parse_path(rest)

def load(datadir):
    shapes = []
    for L in LAYERS:
        p = os.path.join(datadir, L + '.txt')
        if not os.path.exists(p): continue          # older data sets lack the newer layers
        for k, line in enumerate(open(p).read().split('\n')):
            if line.strip():
                shapes.append(Shape(L, k, line.strip()))
    return shapes

def flatten(subs, scale, tol=0.04):
    """Subpaths -> list of closed polygons (N,2) in design units, flattening error < tol px at `scale`."""
    polys = []
    for seg in subs:
        pts = [seg[0]]; cur = seg[0]
        for s in seg[1:]:
            if s[0] == 'L':
                pts.append(s[1]); cur = s[1]
            else:
                c1, c2, p = s[1], s[2], s[3]
                dd = max(np.abs(cur - 2 * c1 + c2).max(), np.abs(c1 - 2 * c2 + p).max()) * scale
                n = int(np.clip(np.ceil(np.sqrt(6 * dd / (8 * tol))), 1, 200))
                tt = np.arange(1, n + 1) / n
                mt = 1 - tt
                b = (mt**3)[:, None] * cur + (3 * mt * mt * tt)[:, None] * c1 + (3 * mt * tt * tt)[:, None] * c2 + (tt**3)[:, None] * p
                pts.extend(b); cur = p
        P = np.array(pts)
        if len(P) >= 3:
            polys.append(P)
    return polys

def rasterize(polys, scale, ox, oy, Wp, Hp, S=16):
    """Even-odd AA coverage. Pixel coords X = x*scale+ox. Vertical: S subsample rows; horizontal: exact.
    Returns (x0, y0, cov) with cov float32 (h, w) for the clipped bbox, or None."""
    if not polys:
        return None
    E = []
    for P in polys:
        Q = P * scale + np.array([ox, oy])
        E.append(np.concatenate([Q, np.roll(Q, -1, 0)], 1))
    E = np.concatenate(E)
    xmin = max(int(np.floor(E[:, [0, 2]].min())), 0); xmax = min(int(np.ceil(E[:, [0, 2]].max())), Wp)
    ymin = max(int(np.floor(E[:, [1, 3]].min())), 0); ymax = min(int(np.ceil(E[:, [1, 3]].max())), Hp)
    if xmax <= xmin or ymax <= ymin:
        return None
    w, h = xmax - xmin, ymax - ymin
    x0, y0, x1, y1 = E[:, 0] - xmin, E[:, 1] - ymin, E[:, 2] - xmin, E[:, 3] - ymin
    keep = y0 != y1
    x0, y0, x1, y1 = x0[keep], y0[keep], x1[keep], y1[keep]
    ylo, yhi = np.minimum(y0, y1), np.maximum(y0, y1)
    # subsample rows j with centre yc=(j+0.5)/S in [ylo, yhi)
    jlo = np.ceil(ylo * S - 0.5).astype(np.int64); jhi = np.ceil(yhi * S - 0.5).astype(np.int64)
    jlo = np.clip(jlo, 0, h * S); jhi = np.clip(jhi, 0, h * S)
    cnt = jhi - jlo
    m = cnt > 0
    if not m.any():
        return None
    x0, y0, x1, y1, jlo, cnt = x0[m], y0[m], x1[m], y1[m], jlo[m], cnt[m]
    ei = np.repeat(np.arange(len(cnt)), cnt)
    j = jlo[ei] + (np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt))
    yc = (j + 0.5) / S
    xs = x0[ei] + (yc - y0[ei]) * (x1[ei] - x0[ei]) / (y1[ei] - y0[ei])
    order = np.lexsort((xs, j))
    j, xs = j[order], xs[order]
    # even-odd pairing within each row: rows have an even count of crossings for closed polygons
    xa, xb, jr = xs[0::2], xs[1::2], j[0::2]
    xa = np.clip(xa, 0, w); xb = np.clip(xb, 0, w)
    acc = np.zeros((h * S, w + 2), np.float64)
    ia = np.floor(xa).astype(np.int64); ib = np.floor(xb).astype(np.int64)
    same = ia == ib
    np.add.at(acc, (jr[same], ia[same]), (xb - xa)[same])
    d = ~same
    np.add.at(acc, (jr[d], ia[d]), (1 - (xa - ia))[d])
    np.add.at(acc, (jr[d], ib[d]), (xb - ib)[d])
    # full cells ia+1 .. ib-1 via a difference array
    diff = np.zeros((h * S, w + 2), np.float64)
    np.add.at(diff, (jr[d], ia[d] + 1), 1)
    np.add.at(diff, (jr[d], ib[d]), -1)
    acc += np.cumsum(diff, 1)
    cov = acc[:, :w].reshape(h, S, w).sum(1) / S
    return xmin, ymin, np.clip(cov, 0, 1).astype(np.float32)

def shading(shape, xs, ys):
    """Colour of a shape at design-space points (arrays) -> (..., 3)."""
    if not shape.grad:
        return np.broadcast_to(shape.c0, xs.shape + (3,))
    d = shape.p1 - shape.p0
    dd = d @ d
    t = np.clip(((xs - shape.p0[0]) * d[0] + (ys - shape.p0[1]) * d[1]) / dd, 0, 1) if dd > 0 else np.zeros_like(xs)
    return shape.c0 + (shape.c1 - shape.c0) * t[..., None]
