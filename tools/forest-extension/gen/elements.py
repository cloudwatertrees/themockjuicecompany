"""Seeded parametric element recipes. Each returns a list of paint.Shape in stacking order (back to front).
All numbers come from the recipe dict R (recipes.json), the instance size and the light angle; positions are design
units, y down. Colours are Lab."""
import numpy as np
from .paint import Shape, Field, linear, smooth_linear, radial, noise
from .shapes import arc, finish, leaflet, lobe_chain, thin_strip, sub_curve, STEP
from .geom import Noise1, resample_open

def L3(v): return np.asarray(v, float)

def light_vec(deg):
    a = np.radians(deg); return np.array([np.cos(a), -np.sin(a)])

def shade(base, centre, extent, light_deg, amount):
    """Field: base Lab with a light gradient of +-amount (Lab) across `extent` units along the light direction."""
    v = light_vec(light_deg); c = np.asarray(centre, float)
    return Field(base, [linear(c - v * extent, c + v * extent, -np.asarray(amount, float), np.asarray(amount, float))])

def jit(rng, lab, sd):
    return np.asarray(lab, float) + rng.normal(0, 1, 3) * np.asarray(sd, float)

MESH_CELL = 4.0       # working-tree art: ~4 unit cells from ~160 units^2 up (largest mesh 206 per side, cap 240)
MESH_2X2_BELOW = 100.0
FLAT_BELOW = 10.0

def cell_for(area):
    return 1e9 if area < MESH_2X2_BELOW else MESH_CELL

def mk(layer, loop, fill, role, flat_below=FLAT_BELOW):
    """Shape with the original's fill rule: flat under 10 units^2, 2x2 mesh under 100, 4-unit cells above."""
    from .geom import poly_area
    A = abs(poly_area(loop))
    if A < flat_below and callable(fill):
        c = np.mean(loop, 0); fill = fill(np.array([c[0]]), np.array([c[1]]))[0]
    return Shape(layer, [loop], fill, cell=cell_for(A), role=role, maxn=240)


def skirt(cx, yt, yb, hw, rng, n_lobes=2, droop=0.28, tip_r=0.10, lobe_depth=0.22, top_w=0.22):
    """One fir/tree tier as seen from the front: narrow top, sides sweeping out to slightly drooping rounded tips,
    lobed bottom edge (n_lobes per side). Returns a closed loop."""
    h = yb - yt
    def half(sg):
        p0 = np.array([cx + sg * top_w * hw, yt])
        tip = np.array([cx + sg * hw, yb - droop * h])
        ctrl = np.array([cx + sg * 0.62 * hw, yt + 0.42 * h])
        s = np.linspace(0, 1, 14)[:, None]
        side = (1 - s) ** 2 * p0 + 2 * (1 - s) * s * ctrl + s ** 2 * tip
        r = tip_r * hw
        cap = arc(tip + [-sg * r * 0.3, r * 0.2], r, (-np.pi / 2 if sg > 0 else -np.pi / 2), (np.pi / 2 if sg > 0 else 3 * np.pi / 2), 7)
        if sg < 0: cap = arc(tip + [r * 0.3, r * 0.2], r, -np.pi / 2, -3 * np.pi / 2, 7)
        a = cap[-1]; b = np.array([cx, yb])
        bot = lobe_chain(a, b, n_lobes, lobe_depth * abs(a[0] - b[0]) / n_lobes, rng, outward=(-1 if sg > 0 else 1))
        return np.vstack([side, cap, bot[1:]])
    R_ = half(1); L_ = half(-1)
    return np.vstack([R_, L_[::-1][1:]])

def spire(cx, yt, yb, w, rng, leaf_pairs=2):
    """Narrow rounded top of a fir with small leaf pairs angled up-out along its sides."""
    r = w / 2
    pts = [arc((cx, yt + r), r, np.pi, 2 * np.pi, 10)]
    right = []; left = []
    ys = np.linspace(yt + 2.5 * r, yb, leaf_pairs + 2)[1:-1]
    for yy in ys:
        L = w * rng.uniform(0.55, 0.8)
        right += [(cx + r, yy - 0.6 * L), (cx + r + 0.8 * L, yy - 0.15 * L), (cx + r + 0.25 * L, yy + 0.1 * L)]
        left += [(cx - r, yy - 0.6 * L), (cx - r - 0.8 * L, yy - 0.15 * L), (cx - r - 0.25 * L, yy + 0.1 * L)]
    right += [(cx + r * 1.1, yb)]; left += [(cx - r * 1.1, yb)]
    return np.vstack([pts[0], np.array(right), np.array(left)[::-1]])


def tooth_outline(cx, Y, Ht, rng, spire_hw, levels, t_bot, hang_n, hang_r, t_top=0.0):
    """Fir tier contour as one loop: rounded spire top, then per level (t_notch, reach, rise, drop) on each side a deep
    notch at the column, a finger rising up/out to a rounded tip and its outer edge falling to the next notch; the
    bottom is a chain of round hanging lobes. All lengths are fractions of Ht."""
    def side(sg):
        pts = [arc((cx, Y(t_top) + spire_hw * Ht), spire_hw * Ht, -np.pi / 2, -np.pi / 2 + sg * np.pi / 2, 6)]
        col = spire_hw
        for (tn, reach, rise, drop, col_w) in levels:
            j = rng.normal(0, 1, 4) * 0.012
            notch = np.array([cx + sg * col_w * Ht, Y(tn + j[0])])
            tip = np.array([cx + sg * (col_w + reach * 0.75 + j[1]) * Ht, Y(tn - rise + j[2])])
            rt = 0.05 * Ht
            outer = np.array([cx + sg * (col_w + reach + j[3]) * Ht, Y(tn - rise + drop * 0.5)])
            low = np.array([cx + sg * (col_w + reach * 0.85) * Ht, Y(tn + drop * 0.9)])
            inner_mid = notch + (tip - notch) * 0.5 + np.array([-sg * 0.01 * Ht, 0])
            cap = arc(tip + [0, rt], rt, -np.pi / 2 - sg * 0.9, -np.pi / 2 + sg * 0.9, 6)
            pts += [notch[None], inner_mid[None], cap, outer[None], low[None]]
        return np.vstack(pts)
    R_, L_ = side(1), side(-1)
    a = R_[-1]; b = L_[-1]
    xs = np.linspace(a[0], b[0], hang_n + 2)[1:-1]
    bot = [a]
    for xx in xs:
        r = hang_r * Ht * rng.uniform(0.8, 1.2); yy = Y(t_bot) - r * 0.2
        bot.append(arc((xx, yy), r, 0.0, np.pi, 8))
    bot.append(b)
    return np.vstack([R_, np.vstack([np.atleast_2d(q) for q in bot]), L_[::-1]])

# ------------------------------------------------------------------------------------------------------------------
def fir(rng, x, y, Ht, R, light_deg=90.0, layer='pines'):
    """Small fir ('pines' layer), back to front: pale halo, ground patch, under-shadow, dark bottom fronds, dark side
    fronds, mid bottom tier, light tiers (lower first, upper overlapping), spire, crevices, rims, flecks.
    (x, y) = base centre, Ht = tip-to-base height. Every light piece shares one field, so overlaps are seamless and
    tier edges read only through the field's under-lobe shadows and the rims (as in the traced single body region)."""
    C = R['colours']; out = []
    yT = y - Ht
    Y = lambda t: yT + t * Ht
    m = int(rng.choice(R['tiers']))
    tb = np.sort(rng.uniform(*np.array(R['tier_bottom_t'][str(m)]).T))
    hw = np.array([rng.uniform(*r) for r in R['tier_hw'][str(m)]]) * Ht
    lean = rng.uniform(-1, 1) * R['lean'] * Ht
    X = lambda t: x + lean * (1 - t)
    # --- halo
    hh = R['halo']; n = 48; tt = np.linspace(0, 1, n)
    ys = Y(hh['top_t']) + tt * (Y(hh['bottom_t']) - Y(hh['top_t']))
    ws = hh['hw'] * Ht * (0.12 + 0.88 * np.clip(tt / 0.9, 0, 1)) * np.where(tt < 0.05, np.sqrt(np.clip(tt / 0.05, 0, 1)), 1) + 4
    halo = np.vstack([np.c_[X(tt) + ws, ys], np.c_[X(tt) - ws, ys][::-1]])
    halo = finish(halo, rng, wob=hh['wobble'] * Ht / 250, k1=45)
    fH = Field(C['halo'], [noise(rng, 30, [1.0, 0.5, 1.3]), linear((x, Y(0)), (x, Y(1.1)), [1.0, 0, -1.5], [-1.0, 0, 1.5])])
    out.append(mk(layer, halo, fH, 'halo'))
    sg = 1 if rng.random() < 0.5 else -1
    i0 = int(n * (0.25 if sg > 0 else 1.25)) % (2 * n)
    seg = halo[(np.arange(len(halo)) * 1)]
    k0 = int(len(halo) * (0.18 if sg > 0 else 0.62)); k1 = int(len(halo) * (0.42 if sg > 0 else 0.86))
    rim = halo[k0:k1]
    inner = rim[::-1] + np.array([-sg * hh['hw'] * Ht * 0.45, 0]) + np.c_[np.zeros(len(rim)), np.zeros(len(rim))]
    piece = finish(np.vstack([rim, inner]), rng, wob=1.5, k1=20)
    out.append(mk(layer, piece, fH.plus(lambda X_, Y_: np.broadcast_to(L3([-0.6, 0.3, -1.5]), np.shape(X_) + (3,))), 'halo'))
    # --- ground patch under the base
    g = R['ground']
    gp = finish(np.c_[x + np.cos(np.linspace(0, 2 * np.pi, 36)) * g['hw'] * Ht,
                      Y(g['t']) + np.sin(np.linspace(0, 2 * np.pi, 36)) * g['hh'] * Ht], rng, wob=1.5, k1=18)
    out.append(mk(layer, gp, Field(C['ground'], [noise(rng, 18, [1.5, 0.8, 1.5]),
                                                 radial((x, Y(g['t'])), (g['hw'] * Ht, g['hh'] * Ht), [-3, -1, -2], [3, 1, 0])]), 'ground'))
    # --- dark base: wide crescent ('smile') with upturned tips, darkest band, dark core between the tiers
    fD = Field(C['dark'], [linear((x, Y(0.55)), (x, Y(1.0)), [3, 0, 2], [-3, 0, -2]),
                           shade(L3([0, 0, 0]), (x, Y(0.8)), 0.3 * Ht, light_deg, [2.5, 0, 1]), noise(rng, 20, [1.5, 0.5, 1])])
    bd = R['base']
    tipL = np.array([X(bd['tip_t']) - bd['hw'] * Ht * rng.uniform(0.9, 1.1), Y(bd['tip_t'] + rng.normal(0, 0.02))])
    tipR = np.array([X(bd['tip_t']) + bd['hw'] * Ht * rng.uniform(0.9, 1.1), Y(bd['tip_t'] + rng.normal(0, 0.02))])
    s_ = np.linspace(0, 1, 30)
    low = np.c_[tipL[0] + (tipR[0] - tipL[0]) * s_, np.interp(s_, [0, 0.5, 1], [tipL[1], Y(1.0), tipR[1]])]
    low[:, 1] = tipL[1] + (tipR[1] - tipL[1]) * s_ + (Y(0.95) - (tipL[1] + tipR[1]) / 2) * np.sin(np.pi * s_) ** 0.45
    up = np.c_[tipL[0] + (tipR[0] - tipL[0]) * s_, tipL[1] + (tipR[1] - tipL[1]) * s_ + (Y(bd['inner_t']) - (tipL[1] + tipR[1]) / 2) * np.sin(np.pi * s_) ** 1.2]
    up[:, 1] += 0.02 * Ht * np.sin(np.pi * s_ * int(rng.integers(3, 6))) ** 2
    lowL = lobe_chain(tipR, tipL, int(rng.integers(4, 7)), 0.035 * Ht, rng, outward=-1)
    lowL[:, 1] += (Y(bd['bottom_t']) - (tipL[1] + tipR[1]) / 2) * np.sin(np.pi * (lowL[:, 0] - tipR[0]) / (tipL[0] - tipR[0])) ** 0.6
    out.append(mk(layer, finish(np.vstack([lowL, up[1:-1]]), rng, 0.4), fD, 'dark'))
    band = finish(np.c_[X(0.84) - 0.06 * Ht + np.cos(np.linspace(0, 2 * np.pi, 30)) * bd['band_hw'] * Ht,
                        Y(0.84) + np.sin(np.linspace(0, 2 * np.pi, 30)) * 0.05 * Ht], rng, 0.6)
    out.append(mk(layer, band, Field(C['under'], [noise(rng, 15, [1.5, 0.5, 1])]), 'under'))
    core = finish(np.c_[X(0.66) + np.cos(np.linspace(0, 2 * np.pi, 30)) * bd['core_hw'] * Ht,
                        Y(0.66) + np.sin(np.linspace(0, 2 * np.pi, 30)) * 0.07 * Ht], rng, 0.6)
    out.append(mk(layer, core, fD.plus(lambda X_, Y_: np.broadcast_to(L3([-5, 0, -2]), np.shape(X_) + (3,))), 'dark'))
    sf = R['side_fronds']
    for sg_ in (-1, 1):
        for j in range(int(rng.integers(sf['per_side'][0], sf['per_side'][1] + 1))):
            t0 = rng.uniform(*sf['t']); base = np.array([X(t0) + sg_ * 0.12 * Ht, Y(t0) + 0.05 * Ht])
            ang = np.radians(rng.uniform(*sf['angle'])); Lf = rng.uniform(*sf['len']) * Ht
            P = leaflet(base, base + np.array([sg_ * np.sin(ang), -np.cos(ang)]) * Lf, sf['w'] * Ht * rng.uniform(0.8, 1.2), bend=-sg_ * 0.1, blunt=0.35)
            out.append(mk(layer, finish(P, rng, 0.2, step=2.4), fD.plus(lambda X_, Y_: np.broadcast_to(L3([3, 0, 1]), np.shape(X_) + (3,))), 'dark'))
    # --- candelabra pieces: column + finger lobes pointing up/out + hanging bottom lobes
    def candelabra(t_top, t_bot, hw_top, hw_bot, levels, fld, role, finger_len, finger_ang, finger_w, hang_n, hang_r):
        pcs = []
        col = np.vstack([arc((X(t_top), Y(t_top) + hw_top), hw_top, np.pi, 2 * np.pi, 10),
                         [(X(t_bot) + hw_bot, Y(t_bot))], [(X(t_bot) - hw_bot, Y(t_bot))]])
        pcs.append(finish(col, rng, 0.3))
        for j, tj in enumerate(levels):
            for sg_ in (-1, 1):
                if rng.random() < 0.12: continue
                fr = (tj - t_top) / max(t_bot - t_top, 1e-6); wb = hw_top + (hw_bot - hw_top) * fr
                Lf = rng.uniform(*finger_len) * Ht * (0.7 + 0.6 * fr)
                ang = np.radians(rng.uniform(*finger_ang) + 20 * fr)
                base = np.array([X(tj) + sg_ * wb * 0.2, Y(tj) + Lf * 0.5])
                tip = base + np.array([sg_ * np.sin(ang), -np.cos(ang)]) * Lf
                P = leaflet(base, tip, finger_w * Ht * rng.uniform(0.85, 1.2) * (0.8 + 0.4 * fr), bend=sg_ * rng.uniform(0.0, 0.12), blunt=0.75)
                pcs.append(finish(P, rng, 0.25, step=2.4))
        yb = Y(t_bot); wb = hw_bot
        n_ = hang_n; xs_ = np.linspace(X(t_bot) - wb * 0.85, X(t_bot) + wb * 0.85, n_)
        for xx in xs_:
            r = hang_r * Ht * rng.uniform(0.8, 1.2)
            pcs.append(finish(np.c_[xx + np.cos(np.linspace(0, 2 * np.pi, 20)) * r, yb - r * 0.75 + np.sin(np.linspace(0, 2 * np.pi, 20)) * r * 1.05], rng, 0.2, step=2.4))
        for P in pcs: out.append(mk(layer, P, fld, role))
        return pcs
    lb = R['body']; ml = R['mid_tier']
    def lv(spec):
        out_ = []
        for (tn, reach, rise, drop, colw) in spec:
            out_.append((tn + rng.uniform(-0.02, 0.02), reach * rng.uniform(0.85, 1.15), rise * rng.uniform(0.8, 1.2), drop * rng.uniform(0.85, 1.15), colw))
        return out_
    fM = Field(C['mid'], [linear((x, Y(ml['t'][0])), (x, Y(ml['t'][1])), [-6, -1, -3], [2, 1, 1]), noise(rng, 14, [1.2, 0.5, 1])])
    midP = finish(tooth_outline(X(0.6), Y, Ht, rng, ml['spire_hw'], lv(ml['levels']), ml['t'][1], int(rng.integers(3, 5)), ml['hang_r'], t_top=ml['t'][0]), rng, 0.3)
    # the mid tier's own top is hidden: shift its outline down so its spire sits inside the body
    out.append(mk(layer, midP, fM, 'mid'))
    fB = Field(C['body_top'], [smooth_linear((x, Y(0)), (x, Y(lb['t_bot'])), [0, 0, 0], np.asarray(C['body_bottom']) - np.asarray(C['body_top'])),
                               shade(L3([0, 0, 0]), (x, Y(0.3)), 0.25 * Ht, light_deg, [2.0, 0.5, 1.0]), noise(rng, 16, [1.4, 0.6, 1.0])])
    nl = int(rng.choice(lb['n_levels']))
    spec = lb['levels'][:nl] if nl <= len(lb['levels']) else lb['levels']
    bodyP = finish(tooth_outline(X(0), Y, Ht, rng, lb['spire_hw'], lv(spec), lb['t_bot'], int(rng.integers(3, 5)), lb['hang_r']), rng, 0.3)
    out.append(mk(layer, bodyP, fB, 'body'))
    body = [None, bodyP, midP]
    tiers = [(0, P) for P in body[1:]]
    # --- rims: thin light strips on the lit upper edges of fingers, dark strips on lower edges of hanging lobes
    rm = R['rims']; lv = light_vec(light_deg)
    for _, P in tiers:
        for kind in ('light', 'dark'):
            if rng.random() > rm['p_' + kind]: continue
            N_ = P - P.mean(0); facing = (N_ @ (lv if kind == 'light' else -lv)) / np.maximum(np.linalg.norm(N_, axis=1), 1e-9)
            cand = np.nonzero(facing > 0.5)[0]
            if len(cand) < 4: continue
            a = int(rng.choice(cand)); seg = np.array([P[(a + q) % len(P)] for q in range(int(rng.integers(3, 6)))])
            Q = thin_strip(seg, rm['w'] * rng.uniform(0.8, 1.25), rng, side=-1.0)
            out.append(mk(layer, Q, jit(rng, C['rim_' + kind], [2, 1, 1.5]), 'rim_' + kind, flat_below=12))
    for _ in range(int(rng.integers(*rm['extra']))):
        i0 = int(rng.integers(0, len(halo) - 8)); seg = halo[i0:i0 + int(rng.integers(3, 7))]
        Q = thin_strip(seg, rm['w'] * rng.uniform(0.7, 1.2), rng, side=-1.0)
        out.append(mk(layer, Q, jit(rng, C['rim_light'], [2, 1, 1.5]), 'rim_light'))
    # --- flecks (mostly on the halo / ground, a few dark in the foliage)
    fl = R['flecks']
    for _ in range(int(rng.integers(*fl['n']))):
        dark = rng.random() < fl['p_dark']
        t0 = rng.uniform(0.2, 1.05)
        c0 = (X(t0) + rng.choice([-1, 1]) * rng.uniform(0.15, 0.35) * Ht, Y(t0))
        r = rng.uniform(*fl['r'])
        P = finish(np.c_[c0[0] + np.cos(np.linspace(0, 2 * np.pi, 10)) * r * rng.uniform(0.6, 1.4), c0[1] + np.sin(np.linspace(0, 2 * np.pi, 10)) * r], rng, 0.1, step=1.0)
        out.append(mk(layer, P, jit(rng, C['fleck_dark'] if dark else C['fleck_light'], [2, 1, 1.5]), 'fleck'))
    return out
