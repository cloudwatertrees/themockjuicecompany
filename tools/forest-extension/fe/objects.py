"""Cluster each layer's shapes into objects: connected components of the layer's union coverage at 1x
(shapes are assigned to the component holding most of their own coverage)."""
import numpy as np
from scipy import ndimage as ndi
from .core import *

def layer_objects(S, layer, scale=1.0, min_px=4):
    idx = [k for k, s in enumerate(S) if s.layer == layer]
    Wp, Hp = int(W * scale), int(H * scale)
    union = np.zeros((Hp, Wp), bool); covs = {}
    for k in idx:
        c = rasterize(flatten(S[k].subs, scale), scale, 0, 0, Wp, Hp)
        if c is None: continue
        covs[k] = c; x0, y0, m = c; union[y0:y0 + m.shape[0], x0:x0 + m.shape[1]] |= m > 0.3
    lab, n = ndi.label(union, structure=np.ones((3, 3)))
    objs = {}
    for k, (x0, y0, m) in covs.items():
        sub = lab[y0:y0 + m.shape[0], x0:x0 + m.shape[1]][m > 0.3]
        sub = sub[sub > 0]
        if len(sub) < 1: continue
        o = int(np.bincount(sub).argmax())
        objs.setdefault(o, []).append(k)
    out = []
    for o, ks in objs.items():
        b = np.array([tbox(S[k]) for k in ks])
        box = (b[:, 0].min(), b[:, 1].min(), b[:, 2].max(), b[:, 3].max())
        out.append(dict(layer=layer, shapes=sorted(ks), box=box, px=int((lab == o).sum())))
    out.sort(key=lambda d: (d['box'][1], d['box'][0]))
    return out
