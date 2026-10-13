"""Fills for generated shapes: Lab colour fields evaluated on the bilinear mesh vertices, exactly as the renderer
spans them (path's tight bounds of the *serialised* path, grown by one unit)."""
import numpy as np
from fe.core import rgb2lab, lab2rgb, rgb2hex, hex2rgb, PShape
from art import parse_path
from pbart import tight_bounds
from .geom import path_string, loop_segments, Noise2

def lab(*v):
    return np.array(v, float)

class Field:
    """Colour field in Lab: base + sum of terms. Each term maps (x, y) arrays -> Lab offsets (..., 3)."""
    def __init__(self, base, terms=()):
        self.base = np.asarray(base, float); self.terms = list(terms)
    def __call__(self, x, y):
        out = np.broadcast_to(self.base, np.shape(x) + (3,)).astype(float).copy()
        for t in self.terms: out += t(x, y)
        return out
    def plus(self, *terms):
        return Field(self.base, self.terms + list(terms))

def linear(p0, p1, d0, d1):
    """Lab offset d0 at p0 ramping to d1 at p1 (clamped)."""
    p0, p1, d0, d1 = (np.asarray(v, float) for v in (p0, p1, d0, d1)); ax = p1 - p0; L2 = ax @ ax
    def f(x, y):
        t = np.clip(((x - p0[0]) * ax[0] + (y - p0[1]) * ax[1]) / L2, 0, 1)[..., None]
        return d0 + (d1 - d0) * t
    return f

def smooth_linear(p0, p1, d0, d1):
    """As linear but with a smoothstep ramp (painted soft transition)."""
    p0, p1, d0, d1 = (np.asarray(v, float) for v in (p0, p1, d0, d1)); ax = p1 - p0; L2 = ax @ ax
    def f(x, y):
        t = np.clip(((x - p0[0]) * ax[0] + (y - p0[1]) * ax[1]) / L2, 0, 1); t = (t * t * (3 - 2 * t))[..., None]
        return d0 + (d1 - d0) * t
    return f

def radial(c, r, d_in, d_out=(0, 0, 0), power=1.5):
    """d_in at the centre fading to d_out at radius r (elliptical if r is a pair)."""
    c = np.asarray(c, float); r = np.broadcast_to(np.asarray(r, float), (2,)); d_in, d_out = np.asarray(d_in, float), np.asarray(d_out, float)
    def f(x, y):
        q = np.sqrt(((x - c[0]) / r[0]) ** 2 + ((y - c[1]) / r[1]) ** 2)
        t = np.clip(1 - q, 0, 1) ** power
        return d_out + (d_in - d_out) * t[..., None]
    return f

def noise(rng, scale, amp_lab):
    """Soft blotchy variation: smooth noise times a Lab amplitude vector (painterly unevenness)."""
    n = Noise2(rng, scale); a = np.asarray(amp_lab, float)
    return lambda x, y: n(x, y)[..., None] * a

class Shape:
    """A generated shape: layer, closed loops (point arrays), fill = Lab colour (flat) or Field (mesh)."""
    def __init__(self, layer, loops, fill, cell=None, smooth=True, tension=1.0, maxn=96, role=None, segs=None):
        self.layer, self.fill, self.cell, self.maxn, self.role = layer, fill, cell, maxn, role
        self.loops = [np.asarray(P, float) for P in loops]
        subs = segs if segs is not None else [loop_segments(P, tension, smooth) for P in self.loops]
        self.pathstr = path_string(subs)

    def line(self):
        if callable(self.fill):
            b = tight_bounds(parse_path(self.pathstr)); x0, y0, x1, y1 = b[0] - 1, b[1] - 1, b[2] + 1, b[3] + 1
            nx = int(np.clip(round((x1 - x0) / self.cell) + 1, 2, self.maxn)); ny = int(np.clip(round((y1 - y0) / self.cell) + 1, 2, self.maxn))
            gx, gy = np.meshgrid(np.linspace(x0, x1, nx), np.linspace(y0, y1, ny))
            cols = lab2rgb(self.fill(gx, gy).reshape(-1, 3))
            return '*%d %d %s %s' % (nx, ny, ' '.join(rgb2hex(c) for c in cols), self.pathstr)
        return '%s %s' % (rgb2hex(lab2rgb(np.asarray(self.fill, float))), self.pathstr)

    def pshape(self):
        s = PShape(self.layer, self.line()); s.region = -1
        return s
