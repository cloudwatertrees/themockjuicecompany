"""The extension's path: centreline + normal-offset half-width in extension space (y = 0 at the seam), brown edge band
on the outer side of each bend (tapering in/out at the inflections), cobbles on the band, pebbles on the surface.
The first ~120 u are fitted so that the visible edges continue the live art's edges (seam.json) in position, slope and
curvature."""
import json
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import least_squares
from common import EXT


def seam_edges():
    s = json.load(open(EXT / 'seam.json'))['edges_at_seam']
    q = lambda e: (lambda y: e['x'] + e['dxdy'] * y + 0.5 * e['d2xdy2'] * y * y)
    return {k: q(v) for k, v in s.items()}


class PathModel:
    """centre knots: [(y, x)], half-width knots: [(y, h)], band: list of (y_start, y_full, y_end_full, y_end, side)
    with side +1 = right, -1 = left, plus band width knots [(y, w)]."""
    def __init__(self, centre_knots, half_knots, band_runs, band_w_knots, seam_fit=True):
        E = seam_edges()
        self.E = E
        if seam_fit:
            # fit centre x0, slope s0, curvature k0, half-width h0, dh0 so that the normal-offset edges reproduce the
            # measured left / cream-right edges over y in [-40, 40]
            ys = np.linspace(-40, 40, 17)
            def edges(p, y):
                x0, s0, k0, h0, dh = p
                c = x0 + s0 * y + 0.5 * k0 * y * y
                sl = s0 + k0 * y
                h = h0 + dh * y
                cos = 1 / np.sqrt(1 + sl * sl); sin = sl * cos
                # normal pointing left for a path heading down: (-cos, +sin) in (x, y)
                return (c - h * cos, y + h * sin), (c + h * cos, y - h * sin)
            def res(p):
                (lx, ly), (rx, ry) = edges(p, ys)
                return np.r_[lx - E['path_left'](ly), rx - E['cream_right'](ry)]
            p0 = [514, -0.12, -0.0035, 146, -0.017]
            p = least_squares(res, p0).x
            self.seam_params = p
            x0, s0, k0, h0, dh = p
            pre = [(y, x0 + s0 * y + 0.5 * k0 * y * y) for y in (-80, -40, 0, 40)]
            preh = [(y, h0 + dh * y) for y in (-80, -40, 0, 40)]
            centre_knots = pre + [k for k in centre_knots if k[0] > 60]
            half_knots = preh + [k for k in half_knots if k[0] > 60]
            self.seam_resid = float(np.abs(res(p)).max())
        cy, cx = np.array(centre_knots).T
        self.cs = CubicSpline(cy, cx)
        hy, hh = np.array(half_knots).T
        self.hs = CubicSpline(hy, hh)
        by, bw = np.array(band_w_knots).T
        self.bws = CubicSpline(by, bw)
        self.band_runs = band_runs
        self.y0, self.y1 = cy[0], cy[-1]

    def centre(self, y):
        return self.cs(y)

    def frame(self, y):
        """Centre point, unit tangent and left normal at centreline parameter y."""
        x = self.cs(y); sl = self.cs(y, 1)
        n = np.sqrt(1 + sl * sl)
        T = np.stack([sl / n, 1 / n], -1)
        N = np.stack([-1 / n, sl / n], -1)              # left
        return np.stack([x, y], -1), T, N

    def band_weight(self, y, side):
        """0..1 band presence on `side` at centreline parameter y (smoothstep tapers)."""
        w = np.zeros_like(np.asarray(y, float))
        for a, b, c, d, s in self.band_runs:
            if s != side:
                continue
            up = np.clip((y - a) / max(b - a, 1e-6), 0, 1)
            dn = np.clip((d - y) / max(d - c, 1e-6), 0, 1)
            k = np.minimum(up, dn)
            w = np.maximum(w, k * k * (3 - 2 * k) if True else k)
        return w

    def edge(self, y, offset_fn):
        """Polyline of the curve offset by offset_fn(y) along the left normal (negative = right side)."""
        P, T, N = self.frame(y)
        return P + N * offset_fn(y)[:, None]

    def ribbon(self, y, inner_fn, outer_fn):
        """Closed polygon between two offset curves (offsets along the left normal)."""
        a = self.edge(y, inner_fn); b = self.edge(y, outer_fn)
        return np.vstack([a, b[::-1]])


class PathEdges:
    """Edges of the path as x(y) on a dense y grid (the path always heads downward, so every edge is a function of y).
    Near the seam (y < SEAM_BLEND) each edge is blended from the measured quadratic of the live edge (exact position,
    slope and curvature at y = 0) into the normal-offset model."""
    SEAM_BLEND = 160.0

    def __init__(self, pm, y0=-60.0, y1=1700.0, gap=1.2):
        self.pm = pm
        self.y = np.arange(y0, y1 + 0.5, 1.0)
        t = np.arange(y0 - 200, y1 + 200, 0.5)
        h = pm.hs(t)
        bwr = pm.bws(t) * pm.band_weight(t, +1)
        bwl = pm.bws(t) * pm.band_weight(t, -1)
        def as_fn(off):
            P = pm.edge(t, lambda _: off)
            o = np.argsort(P[:, 1])
            return np.interp(self.y, P[o, 1], P[o, 0])
        self.left = as_fn(h)
        self.right = as_fn(-h)
        self.rband_in = as_fn(-(h + gap))
        self.rband_out = as_fn(-(h + gap + bwr))
        self.lband_in = as_fn(h + gap)
        self.lband_out = as_fn(h + gap + bwl)
        self.rbw = np.interp(self.y, t, bwr); self.lbw = np.interp(self.y, t, bwl)
        E = pm.E
        w = np.clip(self.y / self.SEAM_BLEND, 0, 1); w = w * w * (3 - 2 * w)
        wr_m = np.maximum(self.rband_out - self.rband_in, 0)      # model band widths in y-space
        wl_m = np.maximum(self.lband_in - self.lband_out, 0)
        for name, key in (('left', 'path_left'), ('right', 'cream_right')):
            setattr(self, name, (1 - w) * E[key](self.y) + w * getattr(self, name))
        # band edges ride on the cream edges (fixed gap, band width blended from the measured one at the seam)
        g0 = E['band_left'](0.0) - E['cream_right'](0.0)
        self.rband_in = self.right + (1 - w) * g0 + w * gap
        wr = (1 - w) * (E['band_right'](self.y) - E['band_left'](self.y)) + w * wr_m
        self.rband_out = self.rband_in + wr
        self.lband_in = self.left - gap
        self.lband_out = self.lband_in - wl_m
        self.rbw, self.lbw = wr, wl_m

    def at(self, name, y):
        return np.interp(y, self.y, getattr(self, name))

    def polygon(self, a, b, ylo=None, yhi=None):
        """Closed polygon between edge arrays a (left boundary) and b (right boundary) over [ylo, yhi]."""
        m = np.ones_like(self.y, bool)
        if ylo is not None: m &= self.y >= ylo
        if yhi is not None: m &= self.y <= yhi
        ys = self.y[m]
        A = np.c_[a[m], ys]; B = np.c_[b[m], ys]
        return np.vstack([A, B[::-1]])
