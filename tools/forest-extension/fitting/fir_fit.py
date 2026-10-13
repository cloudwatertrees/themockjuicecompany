"""Fit the fir recipe (gen/fir.py) to each original fir numerically, then write the fitted parameter sets.
Objective (fitting/tone.py): per tone class 1 - IoU + 0.5 * (curvature-histogram L1 + 0.5 |log contour-length ratio|),
weighted by class area. Optimiser: (1+1)-ES with per-parameter steps and the 1/5 success rule, deterministic seed.
usage: python -m fitting.fir_fit OUT.json [ITERS] [CACHE_DIR]"""
import sys, os, json, pickle, time, numpy as np
from fe.core import *
from fe.objects import layer_objects
from fitting.tone import render_classes, objective, soft_objective, classes
from gen.fir import fir, PARAMS, FANS

SCALE = 0.75

def originals(S, cache_dir=None):
    p = cache_dir and os.path.join(cache_dir, 'objects.pkl')
    O = pickle.load(open(p, 'rb')) if p and os.path.exists(p) else {'pines': layer_objects(S, 'pines')}
    out = []
    for o in [o for o in O['pines'] if len(o['shapes']) > 10]:
        T = [S[k] for k in o['shapes']]; b = o['box']
        box = (b[0] - 6, b[1] - 6, b[0] + 200, b[1] + 312)
        c = render_classes(T, box, SCALE)
        from scipy import ndimage as ndi
        lbl, n = ndi.label(c >= 2); sizes = ndi.sum(np.ones_like(lbl), lbl, range(1, n + 1))
        fol = lbl == (1 + int(np.argmax(sizes))); rows = np.nonzero(fol.sum(1) >= 6 * SCALE)[0]
        top, bot = rows.min(), rows.max()
        Ht = (bot - top) / SCALE; ytip = box[1] + top / SCALE; ybase = box[1] + bot / SCALE
        xs = np.nonzero(fol[top:bot].any(0))[0]; cols = np.nonzero(fol[top:bot])[1]
        xc = box[0] + np.median(cols) / SCALE
        out.append(dict(box=box, cls=c, x=xc, y=ybase, Ht=Ht, shapes=T))
    return out

def colours(insts):
    """Colour constants from the originals: halo / ground means and the a*, b* of foliage as linear functions of L*."""
    labs = []; pale = []
    for I in insts:
        img, al = render_box(I['shapes'], I['box'], SCALE); lab = rgb2lab(img + (1 - al[..., None]))
        labs.append(lab[I['cls'] >= 2]); pale.append(lab[I['cls'] == 1])
    F = np.concatenate(labs); Pp = np.concatenate(pale)
    A = np.c_[F[:, 0] - 65, np.ones(len(F))]
    ca = np.linalg.lstsq(A, F[:, 1], rcond=None)[0]; cb = np.linalg.lstsq(A, F[:, 2], rcond=None)[0]
    hi = Pp[Pp[:, 0] > np.median(Pp[:, 0])]; lo = Pp[Pp[:, 0] <= np.median(Pp[:, 0])]
    return dict(halo=[round(float(v), 2) for v in hi.mean(0)], ground=[round(float(v), 2) for v in lo.mean(0)],
                fan_a=round(float(ca[1]), 2), fan_b=round(float(cb[1]), 2), fan_a_slope=round(float(ca[0]), 3), fan_b_slope=round(float(cb[0]), 3),
                rim_light=[80.0, -14.0, 30.0], rim_dark=[56.0, -26.0, 18.0], rim_p=0.35, rim_w=1.9, fleck=[86.0, -8.0, 28.0], flecks=[4, 9])

P0 = dict(halo_dx=-0.03, halo_top=-0.12, halo_bot=1.02, halo_w0=0.08, halo_w1=0.4, halo_p=0.8, halo_wob=3.0, gr_t=1.02, gr_hw=0.3, gr_hh=0.05,
          # fan 0: bottom dark tier (sideways fronds), 1: upper dark tier, 2: mid leaves, 3: light top fan
          t_0=0.72, x_0=0.0, R_0=0.36, a0_0=90.0, spread_0=85.0, n_0=6, w_0=0.42, blunt_0=0.6, fall_0=-0.3, L_0=57.0, tipL_0=3.0, nd_0=0, dt_0=0.1, dspread_0=40.0, dsize_0=0.035, bw_0=0.08,
          t_1=0.5, x_1=0.0, R_1=0.32, a0_1=90.0, spread_1=85.0, n_1=6, w_1=0.42, blunt_1=0.6, fall_1=-0.3, L_1=58.0, tipL_1=3.0, nd_1=3, dt_1=0.14, dspread_1=60.0, dsize_1=0.035, bw_1=0.06,
          t_2=0.58, x_2=-0.05, R_2=0.28, a0_2=-115.0, spread_2=55.0, n_2=5, w_2=0.38, blunt_2=0.7, fall_2=0.2, L_2=67.0, tipL_2=3.0, nd_2=0, dt_2=0.1, dspread_2=40.0, dsize_2=0.035, bw_2=0.03,
          t_3=0.43, x_3=0.03, R_3=0.36, a0_3=-80.0, spread_3=50.0, n_3=6, w_3=0.3, blunt_3=0.7, fall_3=0.3, L_3=76.0, tipL_3=4.0, nd_3=2, dt_3=0.1, dspread_3=50.0, dsize_3=0.035, bw_3=0.02)
STEP = dict(halo_dx=0.02, halo_top=0.03, halo_bot=0.03, halo_w0=0.02, halo_w1=0.03, halo_p=0.1, halo_wob=0.5, gr_t=0.02, gr_hw=0.03, gr_hh=0.01,
            t=0.02, x=0.015, R=0.03, a0=6.0, spread=8.0, n=0.7, w=0.03, blunt=0.08, fall=0.08, L=1.5, tipL=1.0, nd=0.7, dt=0.02, dspread=8.0, dsize=0.006, bw=0.015)
BOUNDS = dict(halo_dx=(-0.3, 0.3), halo_w0=(0.0, 0.3), halo_w1=(0.25, 0.6), halo_top=(-0.3, 0.05), halo_bot=(0.85, 1.15), halo_p=(0.3, 2.5), halo_wob=(0.5, 6), gr_hw=(0.1, 0.6), gr_hh=(0.02, 0.15),
              R=(0.15, 0.55), spread=(20, 110), n=(4, 9), w=(0.25, 0.6), blunt=(0.3, 1.0), fall=(-0.9, 0.9), L=(48, 84), tipL=(-4, 14),
              nd=(0, 6), dt=(0.0, 0.35), dspread=(0, 120), dsize=(0.015, 0.09), bw=(0.0, 0.2))

def step_of(k): return STEP.get(k, STEP.get(k.rsplit('_', 1)[0], 0.02))
def clamp(k, v):
    b = BOUNDS.get(k, BOUNDS.get(k.rsplit('_', 1)[0]))
    return float(np.clip(v, *b)) if b else float(v)

def evaluate(P, I, C):
    sh = [s.pshape() for s in fir(np.random.default_rng(0), I['x'], I['y'], I['Ht'], P, C, jit=0.0, details=False)]
    cg = render_classes(sh, I['box'], SCALE)
    return soft_objective(cg, I['cls'], SCALE)

def es(I, C, P, iters, seed=1, log=None):
    rng = np.random.default_rng(seed)
    best, per = evaluate(P, I, C); sig = 1.0; succ = []
    keys = PARAMS
    for it in range(iters):
        Q = dict(P)
        ks = rng.choice(keys, size=int(rng.integers(1, 6)), replace=False)
        for k in ks: Q[k] = clamp(k, Q[k] + rng.normal(0, step_of(k) * sig))
        f, pq = evaluate(Q, I, C)
        ok = f < best
        if ok: P, best, per = Q, f, pq
        succ.append(ok)
        if len(succ) >= 20:
            r = np.mean(succ[-20:]); sig *= 1.2 if r > 0.2 else 0.85; sig = float(np.clip(sig, 0.15, 3)); succ = succ[-20:]
        if log and it % 100 == 0: log(it, best, per, sig)
    return P, best, per

def coord(I, C, P, sweeps=8, log=None):
    """Coordinate descent: for each parameter, evaluate a grid of offsets (+-3 steps x range factor) and keep the
    best; the range factor halves when a sweep improves the objective by less than 1%."""
    best, per = evaluate(P, I, C); fac = 2.0
    for sw in range(sweeps):
        start = best
        for k in PARAMS:
            st = step_of(k) * fac
            for off in (-3, -2, -1, 1, 2, 3):
                Q = dict(P); Q[k] = clamp(k, P[k] + off * st)
                if Q[k] == P[k]: continue
                f, pq = evaluate(Q, I, C)
                if f < best - 1e-6: best, per, P = f, pq, Q
        if log: log(sw, best, per, fac)
        if best > start * 0.99: fac *= 0.5
    return P, best, per

def main(out, iters=600, cache_dir=None, only=None):
    S = load_original(); insts = originals(S, cache_dir); C = colours(insts)
    if only is not None: insts = [insts[only]]
    res = dict(colours=C, instances=[])
    for j, I in enumerate(insts):
        j = only if only is not None else j
        t0 = time.time()
        f0, p0 = evaluate(P0, I, C)
        print('inst', j, 'x %.1f y %.1f Ht %.1f' % (I['x'], I['y'], I['Ht']), 'f0 %.3f' % f0, p0, flush=True)
        P, f, per = coord(I, C, dict(P0), sweeps=iters, log=lambda it, b, p, s: print('  sweep', it, 'f %.3f' % b, p, 'fac %.2f' % s, flush=True))
        print('inst', j, 'final f %.3f' % f, per, '%.0fs' % (time.time() - t0), flush=True)
        res['instances'].append(dict(frame=dict(x=I['x'], y=I['y'], Ht=I['Ht'], box=I['box']), P=P, f=f, per={str(k): v for k, v in per.items()}))
        json.dump(res, open(out, 'w'), indent=1)

if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 600, sys.argv[3] if len(sys.argv) > 3 else None,
         int(sys.argv[4]) if len(sys.argv) > 4 else None)
