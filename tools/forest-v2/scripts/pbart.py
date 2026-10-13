"""Phase B data model: shapes with flat or bilinear-mesh fills (mesh spans the path's tight bounds), optional blur.
Line formats:  RRGGBB <path>   |   *NX NY C1 .. Cn <path>   (row-major, top-left first)   | optional '~R ' prefix = blur."""
import os, numpy as np
from art import hex2rgb, rgb2hex, parse_path, flatten, rasterize, LAYERS, W, H

def tight_bounds(subs):
    xs, ys = [], []
    for seg in subs:
        cur = np.asarray(seg[0], float); xs.append(cur[0]); ys.append(cur[1])
        for s in seg[1:]:
            if s[0] == 'L':
                p = np.asarray(s[1], float); xs.append(p[0]); ys.append(p[1]); cur = p
            else:
                c1, c2, p = (np.asarray(v, float) for v in s[1:])
                xs.append(p[0]); ys.append(p[1])
                for k in range(2):
                    a = -cur[k] + 3 * c1[k] - 3 * c2[k] + p[k]; b = 2 * (cur[k] - 2 * c1[k] + c2[k]); c = c1[k] - cur[k]
                    ts = []
                    if abs(a) < 1e-12:
                        if abs(b) > 1e-12: ts = [-c / b]
                    else:
                        disc = b * b - 4 * a * c
                        if disc >= 0: ts = [(-b + np.sqrt(disc)) / (2 * a), (-b - np.sqrt(disc)) / (2 * a)]
                    for t in ts:
                        if 0 < t < 1:
                            mt = 1 - t
                            v = mt ** 3 * cur[k] + 3 * mt * mt * t * c1[k] + 3 * mt * t * t * c2[k] + t ** 3 * p[k]
                            (xs if k == 0 else ys).append(v)
                cur = p
    return min(xs), min(ys), max(xs), max(ys)

class PShape:
    __slots__ = ('layer', 'blur', 'nx', 'ny', 'cols', 'pathstr', 'subs', 'box', 'region')
    def __init__(self, layer, line=None, pathstr=None, blur=0.0, nx=0, ny=0, cols=None, region=-1):
        self.layer = layer; self.region = region
        if line is not None:
            blur = 0.0
            if line.startswith('~'):
                b, line = line[1:].split(' ', 1); blur = float(b)
            if line.startswith('*'):
                f = line[1:].split(' ')
                nx, ny = int(f[0]), int(f[1]); cols = np.array([hex2rgb(h) for h in f[2:2 + nx * ny]])
                pathstr = ' '.join(f[2 + nx * ny:])
            else:
                h, pathstr = line.split(' ', 1); cols = hex2rgb(h)[None]; nx = ny = 0
        self.blur, self.nx, self.ny, self.cols, self.pathstr = blur, nx, ny, cols, pathstr
        self.subs = parse_path(pathstr)
        b = tight_bounds(self.subs)
        self.box = (b[0] - 1, b[1] - 1, b[2] + 1, b[3] + 1)   # mesh rect: bounds grown by one unit
    def line(self):
        pre = '~%g ' % self.blur if self.blur > 0 else ''
        if self.nx:
            return pre + '*%d %d %s %s' % (self.nx, self.ny, ' '.join(rgb2hex(c) for c in self.cols), self.pathstr)
        return pre + '%s %s' % (rgb2hex(self.cols[0]), self.pathstr)
    def colour_at(self, X, Y):
        if not self.nx: return np.broadcast_to(self.cols[0], X.shape + (3,))
        x0, y0, x1, y1 = self.box; nx, ny = self.nx, self.ny
        u = np.clip((X - x0) / max(x1 - x0, 1e-9), 0, 1) * (nx - 1); v = np.clip((Y - y0) / max(y1 - y0, 1e-9), 0, 1) * (ny - 1)
        i = np.minimum(u.astype(int), nx - 2); j = np.minimum(v.astype(int), ny - 2)
        fu = (u - i)[..., None]; fv = (v - j)[..., None]
        C = self.cols.reshape(ny, nx, 3)
        return (C[j, i] * (1 - fu) * (1 - fv) + C[j, i + 1] * fu * (1 - fv) +
                C[j + 1, i] * (1 - fu) * fv + C[j + 1, i + 1] * fu * fv)

def bilinear_dense(box, nx, ny, X, Y):
    x0, y0, x1, y1 = box
    u = np.clip((X - x0) / max(x1 - x0, 1e-9), 0, 1) * (nx - 1); v = np.clip((Y - y0) / max(y1 - y0, 1e-9), 0, 1) * (ny - 1)
    i = np.minimum(u.astype(int), nx - 2); j = np.minimum(v.astype(int), ny - 2)
    fu, fv = u - i, v - j
    Wt = np.zeros((len(X), nx * ny))
    r = np.arange(len(X))
    np.add.at(Wt, (r, j * nx + i), (1 - fu) * (1 - fv)); np.add.at(Wt, (r, j * nx + i + 1), fu * (1 - fv))
    np.add.at(Wt, (r, (j + 1) * nx + i), (1 - fu) * fv); np.add.at(Wt, (r, (j + 1) * nx + i + 1), fu * fv)
    return Wt

def load(datadir):
    shapes = []
    for L in LAYERS:
        p = os.path.join(datadir, L + '.txt')
        if not os.path.exists(p): continue          # older data sets lack the newer layers
        for line in open(p).read().split('\n'):
            if line.strip(): shapes.append(PShape(L, line.strip()))
    return shapes

def write(shapes, datadir):
    os.makedirs(datadir, exist_ok=True)
    for L in LAYERS:
        open(os.path.join(datadir, L + '.txt'), 'w').write('\n'.join(s.line() for s in shapes if s.layer == L) + '\n')
