"""v2: merge low-contrast thin bands (the reference's glows and haze rings) into their neighbour in the 1x region map.
A region at most ~6 px wide (EDT max <= THICK) whose mean colour is within TOL (Lab dE76) of a same-layer neighbour's
local colour model joins that neighbour; its fill can carry the gentle variation, and it no longer becomes a separate
thin shape with a wobbly outline. Only bands that also touch a region more than 15 dE away (i.e. run along an object
edge) qualify, so interior highlights stay. High-contrast thin features (outlines, grooves, stems, petal gaps) are untouched.
Then anti-aliasing slivers: 1 px wide pieces (up to 40 px) whose colour lies between two of their non-sliver neighbours
(slivers.py only tests the two most common neighbours, which are often other slivers) are split pixel-wise between them.
usage: v2_halos.py SRC DST [TOL] [THICK]   (out/B bases; writes DST_reg/_layer; run pb_bounds.py DST after)"""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2lab
from slivers import fit_models, evalm
from art import W, H
from score import SP

src, dst = sys.argv[1], sys.argv[2]
tol = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
thick_max = float(sys.argv[4]) if len(sys.argv) > 4 else 3.0
EDGE = 15.0
reg = np.load(src + '_reg.npy'); lay = np.load(src + '_layer.npy')
rl = rgb2lab(np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255)
for it in range(2):
    models = fit_models(reg, rl)
    objs = ndi.find_objects(reg + 1)
    target = np.arange(reg.max() + 1); nm = 0
    for r, sl in enumerate(objs):
        if sl is None: continue
        y0, y1 = max(sl[0].start - 2, 0), min(sl[0].stop + 2, H); x0, x1 = max(sl[1].start - 2, 0), min(sl[1].stop + 2, W)
        sub = reg[y0:y1, x0:x1]; m = sub == r
        if ndi.distance_transform_edt(np.pad(m, 1))[1:-1, 1:-1].max() > thick_max: continue
        alln = np.unique(sub[ndi.binary_dilation(m, iterations=1) & ~m])
        nbrs = [b for b in alln if lay[b] == lay[r] and models[b] is not None and target[b] == b]
        if not nbrs: continue
        ys, xs = np.nonzero(m); X, Y = xs + x0 + 0.5, ys + y0 + 0.5
        cs = rl[y0:y1, x0:x1][m].mean(0)
        # a halo lies along an object edge: it must also touch a strongly different region (interior highlights do not)
        if not any(models[b] is not None and np.linalg.norm(cs - evalm(models[b], X, Y).mean(0)) > EDGE for b in alln): continue
        d = [np.linalg.norm(cs - evalm(models[b], X, Y).mean(0)) for b in nbrs]
        k = int(np.argmin(d))
        if d[k] < tol: target[r] = nbrs[k]; nm += 1
    reg = target[reg]
    ur, reg = np.unique(reg, return_inverse=True); reg = reg.reshape((H, W)); lay = lay[ur]
    print('pass %d: merged %d bands, regions %d' % (it, nm, reg.max() + 1))
for it in range(2):
    models = fit_models(reg, rl)
    objs = ndi.find_objects(reg + 1); sizes = np.bincount(reg.ravel())
    thin = np.zeros(reg.max() + 1, bool)
    for r, sl in enumerate(objs):
        if sl is not None and sizes[r] <= 40 and ndi.distance_transform_edt(np.pad(reg[sl] == r, 1)).max() <= 1.0: thin[r] = True
    out = reg.copy(); nd = 0
    for r in np.nonzero(thin)[0]:
        sl = objs[r]
        y0, y1 = max(sl[0].start - 2, 0), min(sl[0].stop + 2, H); x0, x1 = max(sl[1].start - 2, 0), min(sl[1].stop + 2, W)
        sub = reg[y0:y1, x0:x1]; m = sub == r
        nb = [b for b in np.unique(sub[ndi.binary_dilation(m, structure=np.ones((3, 3), bool), iterations=2) & ~m]) if not thin[b] and models[b] is not None]
        if len(nb) < 2: continue
        ys, xs = np.nonzero(m); X, Y = xs + x0 + 0.5, ys + y0 + 0.5
        cs = rl[y0:y1, x0:x1][m].mean(0); C = {b: evalm(models[b], X, Y).mean(0) for b in nb}
        ok = False
        for i in range(len(nb)):
            for j in range(i + 1, len(nb)):
                ca, cb = C[nb[i]], C[nb[j]]; v = cb - ca; vv = v @ v
                if vv < 25: continue
                t = (cs - ca) @ v / vv
                if 0.05 < t < 0.95 and np.linalg.norm(cs - (ca + t * v)) < 6: ok = True
        if not ok: continue
        costs = np.stack([np.linalg.norm(rl[y0:y1, x0:x1][m] - evalm(models[b], X, Y), axis=1) for b in nb], 1)
        out[y0:y1, x0:x1][m] = np.array(nb)[costs.argmin(1)]; nd += 1
    reg = out
    ur, reg = np.unique(reg, return_inverse=True); reg = reg.reshape((H, W)); lay = lay[ur]
    print('aa pass %d: dissolved %d slivers, regions %d' % (it, nd, reg.max() + 1))
np.save(dst + '_reg.npy', reg.astype(np.int32)); np.save(dst + '_layer.npy', lay.astype(np.int16))
