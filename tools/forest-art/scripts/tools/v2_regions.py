"""v2: 1x region map of the new reference straight from the image (no source shapes): Felzenszwalb fine regions ->
layer per region from the layer map -> Phase B merge (cubic Lab model, same layer only) -> sliver dissolution.
Writes BASE_reg.npy / BASE_layer.npy for pb_bounds.py and pb_tail.sh.
usage: v2_regions.py LAYERMAP.npy BASE [tau] [deg]   (run from the working copy's tools/)"""
import sys, time, numpy as np
from PIL import Image
from skimage.color import rgb2lab
from skimage.segmentation import felzenszwalb
from merge import merge
from slivers import fit_models, dissolve
from art import W, H
from score import SP

layermap, base = np.load(sys.argv[1]), sys.argv[2]
tau = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
deg = int(sys.argv[4]) if len(sys.argv) > 4 else 3
t0 = time.time()
ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
rl = rgb2lab(ref)
fine = felzenszwalb((ref * 255).astype(np.uint8), scale=5, sigma=0.3, min_size=3)
n = fine.max() + 1
# layer per fine region: majority vote; split regions straddling layers so merging never mixes them
key = fine.astype(np.int64) * 64 + layermap
uk, inv = np.unique(key, return_inverse=True)
lab = inv.reshape(fine.shape)
lay = (uk % 64).astype(np.int16)
print('fine regions %d -> %d after layer split (%.0fs)' % (n, lab.max() + 1, time.time() - t0))
roots, st, sse = merge(lab, lay, rl, deg, tau)
reg = roots[lab]
ur, reg = np.unique(reg, return_inverse=True); reg = reg.reshape((H, W)); lay = lay[ur]
print('merged: %d regions (%.0fs)' % (reg.max() + 1, time.time() - t0))
for it in range(2):
    models = fit_models(reg, rl)
    reg, nd, kl = dissolve(reg, rl, models)
    ur, reg = np.unique(reg, return_inverse=True); reg = reg.reshape((H, W)); lay = lay[ur]
    print('sliver pass %d: dissolved %d, kept thin %d, regions %d' % (it, nd, kl, reg.max() + 1))
np.save(base + '_reg.npy', reg.astype(np.int32)); np.save(base + '_layer.npy', lay.astype(np.int16))
sizes = np.bincount(reg.ravel())
print('regions %d, median size %.0f px, <20 px %d (%.0fs)' % (len(sizes), np.median(sizes), (sizes < 20).sum(), time.time() - t0))
