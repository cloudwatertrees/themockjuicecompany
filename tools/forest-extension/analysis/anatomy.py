"""Anatomy of the original scene's element types -> anatomy.json (instances + metrics), used to fit recipes.json.
usage: python -m analysis.anatomy OUT.json CACHE_DIR"""
import sys, os, json, pickle, numpy as np
from fe.core import *
from fe.objects import layer_objects
from fe.anatomy import Composite, instance_metrics

def objs(S, cache_dir):
    p = os.path.join(cache_dir, 'objects.pkl')
    if os.path.exists(p): return pickle.load(open(p, 'rb'))
    O = {L: layer_objects(S, L) for L in LAYERS}; pickle.dump(O, open(p, 'wb')); return O

def in_box(C, k, box):
    s = C.shapes[k]; b = tbox(s); cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    return box[0] <= cx <= box[2] and box[1] <= cy <= box[3]

def instances(S, C, O):
    I = {}
    I['fir'] = [o['shapes'] for o in O['pines'] if len(o['shapes']) > 10]
    bushes = [o['shapes'] for o in O['bushes'] if len(o['shapes']) >= 10]
    I['bush'] = bushes
    fl = [o['shapes'] for o in O['flowers'] if len(o['shapes']) >= 3]
    I['flower_yellow'], I['flower_purple'], I['flower_white'] = [], [], []
    for f in fl:
        m = C.px(f)
        lab = C.lab[m].mean(0) if m.sum() else rgb2lab(mean_rgb(S[f[0]]))
        (I['flower_yellow'] if lab[2] > 35 else I['flower_purple'] if lab[1] > 15 and lab[2] < 15 else I['flower_white']).append(f)
    I['rock'] = [o['shapes'] for o in O['rocks'] if len(o['shapes']) > 10]
    return I

def main(out, cache_dir):
    S = load_original()
    C = Composite(S, 2.0, cache=os.path.join(cache_dir, 'orig_ids2x.npz'))
    O = objs(S, cache_dir)
    I = instances(S, C, O)
    res = {}
    for t, insts in I.items():
        res[t] = []
        for idx in insts:
            m = instance_metrics(C, idx)
            m['shapes'] = [f'{S[k].layer}#{S[k].region}' for k in idx]
            res[t].append(m)
        print(t, len(insts), 'n:', [m['n'] for m in res[t]], 'cells:', [m['cells'] for m in res[t]],
              'light:', [round(m.get('light_deg', -1)) for m in res[t]], 'w:', [round(m['w']) for m in res[t]])
    json.dump(res, open(out, 'w'), indent=1, default=float)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
