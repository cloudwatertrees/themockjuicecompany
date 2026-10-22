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
from render_skia import render
from softzones import soft_zones
from superres import affine_models, superres

SUPERRES = 4
TRACE_TOLERANCE = 0.25   # px, on visible edges
CONTOUR_SMOOTHING = 1.0  # px at SUPERRES x, before curve fitting


def background(ref):
    """Full-canvas rectangle under everything, so no gap can show through."""
    P = [(-4, -4), (941, -4), (941, 1682), (-4, 1682)]
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
    if (W, H) != (937, 1678):
        print(f'warning: layer regions in semantic.py are placed for 937x1678, got {W}x{H}')
    fine = felzenszwalb(ref.astype(np.uint8), scale=5, sigma=0.3, min_size=3)
    step(f'{fine.max() + 1} fine regions')
    fg = assign(ref, fine, border_mask(ref))
    seq = dendrogram(fine, np.dstack([ref, luma(ref)]), fg)
    lab, grp = global_cut(fine, fg, seq, args.regions)
    step(f'{lab.max() + 1} regions after merging')
    LU = superres(lab, ref, affine_models(lab, ref), SUPERRES)
    step('boundaries re-placed')
    shapes = [background(ref)] + build(lab, LU, grp, GROUPS, ref, SUPERRES, TRACE_TOLERANCE, work=args.work,
                                       workers=args.workers, sigma_u=CONTOUR_SMOOTHING, tag='run')
    step(f'{len(shapes)} shapes traced')
    zones = None if args.no_soft else soft_zones(ref)
    size, nseg, counts = emit(shapes, args.out, zones=zones)
    step(f'wrote {args.out}: {size / 1e6:.2f} MB, {nseg} segments, shapes per layer {counts}')
    print('crisp preview (Skia, no soft pass):', fmt(scores(ref, render(shapes, W, H))))


if __name__ == '__main__':
    main()
