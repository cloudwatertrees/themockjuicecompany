"""Image -> layered SwiftUI vector illustration.

    python pipeline.py art.png --out ForestPathIllustration.swift [--regions 10000]

Steps: over-segment, assign each piece to a named layer, merge to N regions within layers, re-place
boundaries at 4x resolution, trace to cubic Beziers, then write the Swift file with a soft-shading mask."""
import argparse
import os
import time

import numpy as np
from skimage.segmentation import felzenszwalb

from dendro import dendrogram, global_cut
from emit_swift import emit
from hf_groups import GROUPS, assign
from hf_vec import build
from masks import border_mask
from metrics import fmt, load, luma, scores
try:
    from render_skia import render          # preview score only
except ImportError:
    render = None
from softzones import soft_zones
from superres import affine_models, superres
from slivers import dissolve
from meshfill import mesh_fills

SUPERRES = int(os.environ.get('SUPERRES', 4))
INPUT_SCALE = float(os.environ.get('INPUT_SCALE', 1))  # input pixels per design unit; output is in design units
FZ_MIN = int(os.environ.get('FZ_MIN', 3))            # Felzenszwalb min_size
TRACE_TOLERANCE = float(os.environ.get('TRACE_TOLERANCE', 0.25))     # px, on visible edges
CONTOUR_SMOOTHING = float(os.environ.get('CONTOUR_SMOOTHING', 1.0))  # px at SUPERRES x, before curve fitting
EDGE_TAU = float(os.environ.get('EDGE_TAU', 0))                        # edge-aware merging (0 = off), source contrast units


def background(ref):
    """Full-canvas rectangle under everything, so no gap can show through."""
    H, W = ref.shape[:2]
    P = [(-4, -4), (W + 4, -4), (W + 4, H + 4), (-4, H + 4)]
    segs = [np.array([P[i], P[i], P[(i + 1) % 4], P[(i + 1) % 4]], float) for i in range(4)]
    return dict(group='meadow', fill=dict(type='flat', color=ref.reshape(-1, 3).mean(0)), subpaths=[segs])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('image')
    ap.add_argument('--out', required=True, help='Swift file to write')
    ap.add_argument('--regions', type=int, default=10000)
    ap.add_argument('--work', default='.work', help='scratch directory')
    ap.add_argument('--workers', type=int, default=7)
    ap.add_argument('--no-soft', action='store_true', help='skip the soft-shading zones')
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    t0 = time.time()

    def step(msg):
        print(f'[{time.time() - t0:6.1f}s] {msg}', flush=True)

    ref = load(args.image)
    H, W = ref.shape[:2]
    fine = felzenszwalb(ref.astype(np.uint8), scale=5, sigma=0.3, min_size=FZ_MIN)
    step(f'{fine.max() + 1} fine regions')
    fg = assign(ref, fine, border_mask(ref))
    seq = dendrogram(fine, np.dstack([ref, luma(ref)]), fg, edge_tau=EDGE_TAU)
    lab, grp = global_cut(fine, fg, seq, args.regions)
    step(f'{lab.max() + 1} regions after merging')
    if os.environ.get('SLIVERS', '1') != '0':
        lab, grp, ns = dissolve(lab, grp, ref)
        step(f'{ns} anti-aliasing slivers dissolved, {lab.max() + 1} regions')
    LU = superres(lab, ref, affine_models(lab, ref), SUPERRES)
    step('boundaries re-placed')
    shapes = [background(ref)] + build(lab, LU, grp, GROUPS, ref, SUPERRES, TRACE_TOLERANCE, work=args.work,
                                       workers=args.workers, sigma_u=CONTOUR_SMOOTHING, tag='run')
    step(f'{len(shapes)} shapes traced')
    import pickle
    pickle.dump(shapes, open(os.path.join(args.work, 'shapes.pkl'), 'wb'))
    if render is not None:
        print('crisp preview (Skia, no soft pass, input resolution):', fmt(scores(ref, render(shapes, W, H))))
    if INPUT_SCALE != 1:
        k = 1 / INPUT_SCALE
        for sh in shapes:
            sh['subpaths'] = [[np.asarray(b) * k for b in segs] for segs in sh['subpaths']]
            if sh['fill']['type'] != 'flat':
                sh['fill']['p0'] = np.asarray(sh['fill']['p0']) * k
                sh['fill']['p1'] = np.asarray(sh['fill']['p1']) * k
    if os.environ.get('MESH', '0') != '0':
        nm = mesh_fills(shapes, lab, ref, scale=1 / INPUT_SCALE, cell=float(os.environ.get('MESH_CELL', 5)), min_area=int(os.environ.get('MESH_MIN', 120)))
        step(f'{nm} mesh-gradient fills')
    zones = None if args.no_soft else soft_zones(ref)
    size, nseg, counts = emit(shapes, args.out, zones=zones)
    step(f'wrote {args.out}: {size / 1e6:.2f} MB, {nseg} segments, shapes per layer {counts}')


if __name__ == '__main__':
    main()
