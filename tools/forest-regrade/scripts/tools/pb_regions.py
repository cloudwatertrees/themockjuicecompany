"""Phase B stage 1: regions at 1x with layer ids (cost-based merging of Phase A shapes + sliver dissolution)."""
import sys, numpy as np
from PIL import Image
from skimage.color import rgb2lab
from art import load, LAYERS, W, H
from regions import shape_labels
from merge import merge
from slivers import fit_models, dissolve
SP = '/tmp/work/'

def run(src, out, deg=3, tau=6.0):
    shapes = load(src); layer_of = np.array([LAYERS.index(s.layer) for s in shapes])
    lab = shape_labels(shapes)
    ul, inv = np.unique(lab, return_inverse=True); inv = inv.reshape(lab.shape); lay = layer_of[ul]
    ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
    rl = rgb2lab(ref)
    roots, st, sse = merge(inv, lay, rl, deg, tau)
    reg = roots[inv]
    for it in range(2):
        ur, reg = np.unique(reg, return_inverse=True); reg = reg.reshape((H, W)); lay = lay[ur] if it == 0 else lay[ur]
        models = fit_models(reg, rl)
        reg, nd, kl = dissolve(reg, rl, models)
        print('pass %d: dissolved %d, kept thin %d' % (it, nd, kl))
    ur, reg = np.unique(reg, return_inverse=True); reg = reg.reshape((H, W)); lay = lay[ur]
    np.save(out + '_reg.npy', reg.astype(np.int32)); np.save(out + '_layer.npy', lay.astype(np.int16))
    print('regions', reg.max() + 1)

if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
