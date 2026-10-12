"""Prepend a full-canvas grass base to the meadow layer (as the original data had): a coarse bilinear mesh fitted
to the reference over the meadow layer's visible pixels, smoothly interpolated under everything else. It is fully
covered in the complete scene; it only shows when layers are drawn on their own or moved."""
import sys, os, numpy as np
from PIL import Image
from scipy import sparse
from scipy.sparse.linalg import spsolve
from meshfit import bilinear_weights
from pbart import load, write, PShape
from art import W, H, LAYERS
SP = '/tmp/work/'

def run(base, datadir, cell=48.0, margin=16):
    reg = np.load(base + '_reg.npy'); lay = np.load(base + '_layer.npy')
    ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
    meadow = lay[reg] == LAYERS.index('meadow')
    ys, xs = np.nonzero(meadow[::2, ::2]); ys, xs = ys * 2, xs * 2
    x0, y0, x1, y1 = -margin, -margin, W + margin, H + margin
    pathstr = 'M%d %dl%d 0l0 %dl%d 0Z' % (x0, y0, x1 - x0, y1 - y0, -(x1 - x0))
    sh = PShape('meadow', pathstr=pathstr)
    nx, ny = int(round((sh.box[2] - sh.box[0]) / cell)) + 1, int(round((sh.box[3] - sh.box[1]) / cell)) + 1
    # data term + membrane (first differences): harmonic extension under other layers, no overshoot
    Bw = bilinear_weights(xs + 0.5, ys + 0.5, sh.box, nx, ny)
    idx = np.arange(nx * ny).reshape(ny, nx); rows = []
    for a_, b_ in [(idx[:, :-1], idx[:, 1:]), (idx[:-1], idx[1:])]:
        a_, b_ = a_.ravel(), b_.ravel(); k = len(a_)
        rows.append(sparse.csr_matrix((np.concatenate([np.ones(k), -np.ones(k)]), (np.tile(np.arange(k), 2), np.concatenate([a_, b_]))), shape=(k, nx * ny)))
    Rm = sparse.vstack(rows)
    A = (Bw.T @ Bw + 50.0 * (Rm.T @ Rm) + 1e-6 * sparse.identity(nx * ny)).tocsc()
    V = np.stack([spsolve(A, Bw.T @ ref[ys, xs][:, c]) for c in range(3)], 1)
    sh.nx, sh.ny, sh.cols = nx, ny, np.clip(V, 0, 1)
    shapes = load(datadir)
    write([sh] + shapes, datadir)
    print('base mesh %dx%d added to meadow' % (nx, ny))

if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
