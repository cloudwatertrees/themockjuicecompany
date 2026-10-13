"""Sample firs from the fitted parameter sets, place them on the original's lower layers at the original fir's spot,
render originals vs generated at device 3x (393x852 @3x framing: 1.5232 px/unit), and compute the Stage 1 numbers.
usage: python -m fitting.fir_report FIT.json OUT_PREFIX CACHE_DIR [N]"""
import sys, json, numpy as np
from fe.core import *
from fe.anatomy import Composite, instance_metrics
from fe import nocopy
from fitting.fir_fit import originals, colours
from gen.fir import fir, PARAMS

def sample_params(fits, rng):
    A = np.array([[f['P'][k] for k in PARAMS] for f in fits]); m = A.mean(0); sd = np.abs(A[0] - A[-1]) / 2
    floor = np.array([0.15 * abs(v) * 0.1 + 1e-3 for v in m])
    return dict(zip(PARAMS, m + rng.normal(0, 1, len(m)) * np.maximum(sd, floor)))

def main(fitp, pre, cache, N=5):
    F = json.load(open(fitp)); S = load_original(); I = originals(S, cache); C = F['colours']
    from gen.paint import Shape
    b0 = originals(S, cache)[0]['box']
    backing = Shape('meadow', [np.array([[b0[0] - 5, b0[1] - 5], [b0[2] + 5, b0[1] - 5], [b0[2] + 5, b0[3] + 5], [b0[0] - 5, b0[3] + 5]])], [84.6, -8.5, 29.8]).pshape()
    under = [backing] + [s for s in S if LAYERS.index(s.layer) < LAYERS.index('pines')]
    over = [s for s in S if LAYERS.index(s.layer) > LAYERS.index('pines')]
    A = I[0]; box = A['box']
    panels, gens = [], []
    for J in I:
        img, _ = render_box(S, J['box'], DEV); panels.append(img)
    for i in range(N):
        rng = np.random.default_rng(100 + i)
        P = sample_params(F['instances'], rng)
        Ht = rng.uniform(min(J['Ht'] for J in I), max(J['Ht'] for J in I))
        G = [g.pshape() for g in fir(rng, A['x'], A['y'], Ht, P, C, jit=1.0, details=True)]
        gens.append(G)
        img, _ = render_box(under + G, box, DEV); panels.append(img)
    h = max(p.shape[0] for p in panels); w = max(p.shape[1] for p in panels)
    pad = lambda p: np.pad(p, ((0, h - p.shape[0]), (0, w - p.shape[1]), (0, 0)), constant_values=1)
    row1 = np.concatenate([pad(p) for p in panels[:4]], 1); row2 = np.concatenate([pad(p) for p in panels[4:]] + [np.ones((h, w * (8 - len(panels)), 3))] * (len(panels) < 8), 1)
    save(np.concatenate([row1, row2[:, :row1.shape[1]]], 0), pre + '_3x.png')
    # metrics
    Corig = Composite(S, 2.0, cache=cache + '/orig_ids2x.npz')
    import pickle
    O = pickle.load(open(cache + '/objects.pkl', 'rb'))
    om = [instance_metrics(Corig, o['shapes']) for o in O['pines'] if len(o['shapes']) > 10]
    gm = []
    for G in gens:
        Cg = Composite(under + G, 2.0, box=box)
        idx = list(range(len(under), len(under) + len(G)))
        gm.append(instance_metrics(Cg, idx))
    def mean(ms, k): return float(np.mean([m[k] for m in ms]))
    rep = {}
    for k in ('n', 'cells'):
        o, g = mean(om, k), mean(gm, k); rep[k] = dict(orig=o, gen=g, rel=round(g / o - 1, 3))
    lo = np.mean([m['lab_mean'] for m in om], 0); lg = np.mean([m['lab_mean'] for m in gm], 0)
    rep['palette_dE76'] = round(float(np.linalg.norm(lo - lg)), 2); rep['lab_orig'] = lo.round(2).tolist(); rep['lab_gen'] = lg.round(2).tolist()
    ang = lambda ms: float(np.degrees(np.angle(np.mean([np.exp(1j * np.radians(m['light_deg'])) for m in ms]))) % 360)
    rep['light'] = dict(orig=round(ang(om), 1), gen=round(ang(gm), 1))
    rw = lambda ms: float(np.mean([m['rim_width_med'] for m in ms if m['rim_width_med']]))
    rep['rim_width'] = dict(orig=round(rw(om), 2), gen=round(rw(gm), 2))
    so = lambda ms: float(np.mean([np.hypot(*m['dark_offset']) / np.sqrt(m['area']) for m in ms]))
    rep['shadow_offset_rel'] = dict(orig=round(so(om), 3), gen=round(so(gm), 3))
    allg = [s for G in gens for s in G]
    dmin, matches = nocopy.check(allg, S)
    rep['nocopy'] = dict(generated_shapes=len(allg), min_distance=round(dmin, 3), matches=len(matches), eps=nocopy.EPS)
    rep['per_instance'] = dict(orig=[(m['n'], m['cells'], round(m['light_deg'])) for m in om], gen=[(m['n'], m['cells'], round(m['light_deg'])) for m in gm])
    json.dump(rep, open(pre + '_report.json', 'w'), indent=1); print(json.dumps(rep, indent=1))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 5)
