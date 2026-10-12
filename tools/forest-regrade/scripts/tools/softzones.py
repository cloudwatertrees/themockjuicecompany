"""Soft zones from the reference: soft where a sigma-2.5 blur leaves the reference visibly unchanged.
Traced at 2x, extended off-canvas, one closed subpath per line (even-odd)."""
import sys, os, numpy as np
from scipy import ndimage as ndi
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000
from trace import trace, upsample_mask
from pathio import path_str
from art import W, H
SP = '/tmp/work/'

def soft_map(ref, tau=3.0, grow=1):
    bl = np.stack([ndi.gaussian_filter(ref[..., c], 2.467, mode='nearest') for c in range(3)], -1)
    e = deltaE_ciede2000(rgb2lab(ref), rgb2lab(bl))
    hard = ndi.binary_dilation(e > tau, iterations=grow)
    soft = ~hard
    soft = ndi.binary_opening(soft, iterations=1)
    lab, n = ndi.label(soft); sz = ndi.sum(np.ones_like(e), lab, range(1, n + 1))
    soft = np.isin(lab, 1 + np.nonzero(sz >= 24)[0])
    lab, n = ndi.label(~soft); sz = ndi.sum(np.ones_like(e), lab, range(1, n + 1))
    soft |= np.isin(lab, 1 + np.nonzero(sz < 6)[0])
    return soft

def write_zones(soft, path, U=2, ext=12, sigma=1.2, opt=1.0):
    m = np.pad(soft, ext, mode='edge')
    subs = trace(upsample_mask(np.pad(m, 2), U, sigma=sigma), U, -ext - 2, -ext - 2, turd=8, alphamax=1.1, opt=opt)
    open(path, 'w').write('\n'.join(path_str([s]) for s in subs) + '\n')
    return len(subs)

if __name__ == '__main__':
    ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
    tau = float(sys.argv[2])
    soft = soft_map(ref, tau)
    n = write_zones(soft, sys.argv[1])
    print('tau %.1f: soft fraction %.3f, %d subpaths' % (tau, soft.mean(), n))
