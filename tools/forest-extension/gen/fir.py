"""Fir recipe (layer 'pines'): a pale halo, a ground patch and a stack of leaf fans (bottom fan first).
Each fan = leaflets radiating from a centre, sharing one radial colour field (fan tone at the centre, lighter towards
the tips), plus 'drops' (light leaf tips hanging over the fan below). Geometry is a flat parameter dict P fitted to the
original instances (fitting/fir_fit.py); `jit` scales the random per-instance variation (0 = deterministic mean form
used while fitting)."""
import numpy as np
from .paint import Field, linear, radial, noise
from .shapes import arc, finish, leaflet, thin_strip
from .elements import mk, jit as jlab, L3, light_vec, shade

FANS = 4
PARAMS = ['halo_dx', 'halo_top', 'halo_bot', 'halo_w0', 'halo_w1', 'halo_p', 'halo_wob',
          'gr_t', 'gr_hw', 'gr_hh'] + \
         [f'{k}_{i}' for i in range(FANS) for k in
          ('t', 'x', 'R', 'a0', 'spread', 'n', 'w', 'blunt', 'fall', 'L', 'tipL', 'nd', 'dt', 'dspread', 'dsize', 'bw')]

def fan_leaf_dirs(a0, spread, n):
    if n <= 1: return np.array([a0])
    return np.linspace(a0 - spread, a0 + spread, n)

def fir(rng, x, y, Ht, P, C, light_deg=90.0, layer='pines', jit=1.0, details=True):
    """(x, y) = base centre of the foliage (bottom), Ht = tip-to-base height. P: params (fractions of Ht, degrees,
    Lab L*), C: colours (Lab). Returns shapes back to front."""
    out = []
    J = lambda sd: rng.normal(0, sd * jit) if jit > 0 else 0.0
    Y = lambda t: y - Ht + t * Ht
    # --- halo
    tt = np.linspace(0, 1, 48)
    ys = Y(P['halo_top']) + tt * (Y(P['halo_bot']) - Y(P['halo_top']))
    ws = Ht * (P['halo_w0'] + (P['halo_w1'] - P['halo_w0']) * tt ** P['halo_p']) * np.where(tt < 0.06, np.sqrt(tt / 0.06), 1) + 2
    hx = x + P['halo_dx'] * Ht * (1 - tt)
    halo = np.vstack([np.c_[hx + ws, ys], np.c_[hx - ws, ys][::-1]])
    halo = finish(halo, rng if jit > 0 else np.random.default_rng(0), wob=P['halo_wob'] * Ht / 250, k1=45)
    fH = Field(C['halo'], [noise(rng, 30, [1.0, 0.5, 1.3]), linear((x, Y(0)), (x, Y(1.1)), [1.0, 0, -1.5], [-1.0, 0, 1.5])])
    out.append(mk(layer, halo, fH, 'halo'))
    # --- ground patch
    gp = finish(np.c_[x + np.cos(np.linspace(0, 2 * np.pi, 36)) * P['gr_hw'] * Ht,
                      Y(P['gr_t']) + np.sin(np.linspace(0, 2 * np.pi, 36)) * P['gr_hh'] * Ht], rng, wob=1.2 * jit, k1=18)
    out.append(mk(layer, gp, Field(C['ground'], [noise(rng, 18, [1.5, 0.8, 1.5])]), 'ground'))
    # --- fans, bottom (0) to top (FANS-1)
    lv = light_vec(light_deg)
    leaves_all = []
    for i in range(FANS):
        g = lambda k: P[f'{k}_{i}']
        cx = x + (g('x') + J(0.01)) * Ht; cy = Y(g('t') + J(0.012)); R = g('R') * Ht * (1 + J(0.06))
        n = max(int(round(g('n'))), 1)
        dirs = fan_leaf_dirs(g('a0') + J(4), g('spread') + J(4), n) + rng.normal(0, 5 * jit, n)
        Lc = g('L'); tipL = g('tipL')
        lab_at = lambda L_: np.array([L_, C['fan_a'] + C['fan_a_slope'] * (L_ - 65), C['fan_b'] + C['fan_b_slope'] * (L_ - 65)])
        base = lab_at(Lc); tip = lab_at(Lc + tipL)
        fF = Field(base, [radial((cx, cy), (R, R), [0, 0, 0], tip - base, power=1.0),
                          shade(L3([0, 0, 0]), (cx, cy), R, light_deg, [2.5, 0.5, 1.0]), noise(rng, 16, [1.2, 0.5, 1.0])])
        # radial() gives d_in at the centre -> d_out at R: we want base at centre and tip at R
        span = g('spread') if g('spread') > 1e-6 else 1.0
        for d in dirs:
            u = (d - g('a0')) / span
            Ln = R * max(1 - g('fall') * u * u, 0.25) * (1 + J(0.08))
            a = np.radians(d); b0 = np.array([cx + np.clip(u, -1, 1) * g('bw') * Ht, cy])
            tipP = b0 + np.array([np.cos(a) * Ln, np.sin(a) * Ln])
            P_ = leaflet(b0, tipP, g('w') * R * (1 + J(0.1)), bend=J(0.08), blunt=g('blunt'))
            P_ = finish(P_, rng, 0.25 * jit, step=2.4)
            out.append(mk(layer, P_, fF, 'fan%d' % i)); leaves_all.append((i, P_, d))
        # drops: light leaf tips hanging below this fan (over the fan below)
        nd = max(int(round(g('nd'))), 0)
        if nd:
            ddirs = fan_leaf_dirs(90.0, g('dspread'), nd) + rng.normal(0, 6 * jit, nd)
            for d in ddirs:
                a = np.radians(d); Ld = g('dt') * Ht
                c0 = np.array([cx + np.cos(a) * Ld, cy + np.sin(a) * Ld]); r = g('dsize') * Ht * (1 + J(0.12))
                Pd = leaflet(c0 - np.array([np.cos(a), np.sin(a)]) * r * 1.2, c0 + np.array([np.cos(a), np.sin(a)]) * r, r * 1.3, blunt=0.9)
                out.append(mk(layer, finish(Pd, rng, 0.2 * jit, step=2.0), fF, 'drop%d' % i))
    if not details: return out
    # --- rims: thin light strips on lit leaf edges, thin dark strips on shaded edges
    for (i, P_, d) in leaves_all:
        for kind, dirv in (('light', lv), ('dark', -lv)):
            if rng.random() > C['rim_p']: continue
            N_ = P_ - P_.mean(0); f = (N_ @ dirv) / np.maximum(np.linalg.norm(N_, axis=1), 1e-9)
            cand = np.nonzero(f > 0.55)[0]
            if len(cand) < 4: continue
            a = int(rng.choice(cand)); seg = np.array([P_[(a + q) % len(P_)] for q in range(int(rng.integers(3, 6)))])
            out.append(mk(layer, thin_strip(seg, C['rim_w'] * rng.uniform(0.8, 1.25), rng, side=-1.0),
                          jlab(rng, C['rim_' + kind], [2, 1, 1.5]), 'rim_' + kind, flat_below=12))
    for _ in range(int(rng.integers(*C['flecks']))):
        t0 = rng.uniform(0.15, 1.05); c0 = (x + rng.choice([-1, 1]) * rng.uniform(0.2, 0.42) * Ht, Y(t0)); r = rng.uniform(0.8, 2.2)
        Pf = finish(np.c_[c0[0] + np.cos(np.linspace(0, 2 * np.pi, 10)) * r * rng.uniform(0.6, 1.4), c0[1] + np.sin(np.linspace(0, 2 * np.pi, 10)) * r], rng, 0.1, step=1.0)
        out.append(mk(layer, Pf, jlab(rng, C['fleck'], [2, 1, 1.5]), 'fleck'))
    return out
