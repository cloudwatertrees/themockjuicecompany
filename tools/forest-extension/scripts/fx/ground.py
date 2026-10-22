"""Paint buffers: soft colour fields painted on a raster (Gaussian blobs, distance strips, noise) and sampled
bilinearly by shape meshes. Used for the meadow and the path surface so that soft shadows, pale halos and mottling
read as painted regions, and so the fields can be blended into the live art's last row at the seam."""
import json
import numpy as np
from scipy import ndimage as ndi
from art import hex2rgb
from common import EXT
from .paint import Noise, ramp

MEADOW = ramp([(0.0, '7F8E57'), (0.18, '97A262'), (0.35, 'ADB46B'), (0.55, 'C5C777'), (0.72, 'D2D087'),
               (0.86, 'E1DB9D'), (1.0, 'EFE8BC')])


class Buffer:
    """Scalar or RGB raster over a design-space box at `res` samples per unit."""
    def __init__(self, x0, y0, x1, y1, res=0.5, channels=1, fill=0.0):
        self.x0, self.y0, self.res = x0, y0, res
        self.nx = int(np.ceil((x1 - x0) * res)) + 1
        self.ny = int(np.ceil((y1 - y0) * res)) + 1
        shape = (self.ny, self.nx) if channels == 1 else (self.ny, self.nx, channels)
        self.a = np.full(shape, fill, float)
        self.X, self.Y = np.meshgrid(x0 + np.arange(self.nx) / res, y0 + np.arange(self.ny) / res)

    def sample(self, X, Y):
        u = (np.asarray(X) - self.x0) * self.res
        v = (np.asarray(Y) - self.y0) * self.res
        if self.a.ndim == 2:
            return ndi.map_coordinates(self.a, [v.ravel(), u.ravel()], order=1, mode='nearest').reshape(np.shape(X))
        return np.stack([ndi.map_coordinates(self.a[..., c], [v.ravel(), u.ravel()], order=1, mode='nearest')
                         for c in range(self.a.shape[2])], -1).reshape(np.shape(X) + (self.a.shape[2],))

    def blob(self, cx, cy, rx, ry, amount, ang=0.0, power=2.0):
        """Add a soft elliptical blob (Gaussian-like falloff, 1/e at the radii)."""
        c, s = np.cos(ang), np.sin(ang)
        u = ((self.X - cx) * c + (self.Y - cy) * s) / rx
        v = (-(self.X - cx) * s + (self.Y - cy) * c) / ry
        self.a += amount * np.exp(-(u * u + v * v) ** (power / 2))

    def blur(self, sigma_units):
        self.a = ndi.gaussian_filter(self.a, sigma_units * self.res)


def seam_profile():
    """The live art's last-row colours (1 u bins) as an (937, 3) array in 0..1."""
    p = json.load(open(EXT / 'seam.json'))['last_row_profile_hex_1u']
    return np.array([hex2rgb(h) for h in p])


def seam_blend(field, depth=70.0, profile=None, spread=0.6):
    """Wrap an RGB field so that it equals the live art's last-row colour at y <= 0 and eases into `field` by `depth`.
    The profile is blurred horizontally in proportion to y (sigma = spread * y) so that its column-to-column detail
    does not drag down as vertical streaks."""
    P = seam_profile() if profile is None else profile
    xs = np.arange(len(P)) + 0.5
    sig = np.r_[0, np.geomspace(0.5, max(depth * spread, 1), 24)]
    stack = np.stack([P if s == 0 else ndi.gaussian_filter1d(P, s, axis=0, mode='nearest') for s in sig])

    def f(X, Y):
        X = np.asarray(X, float); Y = np.asarray(Y, float)
        base = field(X, Y)
        sy = np.clip(Y, 0, None) * spread
        k = np.clip(np.interp(sy, sig, np.arange(len(sig))), 0, len(sig) - 1)
        k0 = np.floor(k).astype(int); k1 = np.minimum(k0 + 1, len(sig) - 1); fk = (k - k0)[..., None]
        xi = np.clip(X - 0.5, 0, len(P) - 1.0)
        i0 = np.floor(xi).astype(int); i1 = np.minimum(i0 + 1, len(P) - 1); fx = (xi - i0)[..., None]
        g = lambda kk: stack[kk, i0] * (1 - fx) + stack[kk, i1] * fx
        prof = g(k0) * (1 - fk) + g(k1) * fk
        w = np.clip(Y / depth, 0, 1); w = (w * w * (3 - 2 * w))[..., None]
        return prof * (1 - w) + base * w
    return f
