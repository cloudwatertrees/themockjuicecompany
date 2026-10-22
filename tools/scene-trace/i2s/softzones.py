"""Soft zones: the canvas minus a band around every hard colour edge of the reference.

The Swift renderer blurs the scene and keeps the blurred copy only inside these zones, so smooth
shading reads smooth while outlines stay crisp. Edges come from the per-channel colour gradient, so
boundaries between similar-brightness colours are protected too."""
import numpy as np
from scipy import ndimage as ndi
from skimage import measure

from bezier import fit_closed, merge_segments


def soft_zones(ref, edge_threshold=6.0, margin=4.0):
    """Closed subpaths (even-odd) covering everything at least `margin` px from a hard edge."""
    H, W = ref.shape[:2]
    g = np.max(np.stack([np.hypot(ndi.sobel(ndi.gaussian_filter(ref[..., c], 1.0), 1),
                                  ndi.sobel(ndi.gaussian_filter(ref[..., c], 1.0), 0)) / 8 for c in range(3)]), axis=0)
    e = g > edge_threshold
    lbl, n = ndi.label(e)
    sz = np.bincount(lbl.ravel())
    keep = sz >= 20
    keep[0] = False
    e = keep[lbl]
    D = ndi.distance_transform_edt(~e)
    F = np.pad(D, 2, constant_values=1e3)  # zone extends past the canvas edge

    def rect(x0, y0, x1, y1):
        P = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return [np.array([P[i], P[i], P[(i + 1) % 4], P[(i + 1) % 4]], float) for i in range(4)]

    subs = [rect(-8, -8, W + 8, H + 8)]
    for c in measure.find_contours(ndi.gaussian_filter(F, 0.7), margin):
        c = c[:-1] if np.allclose(c[0], c[-1]) else c
        if len(c) < 6:
            continue
        area = 0.5 * abs(np.dot(c[:, 0], np.roll(c[:, 1], 1)) - np.dot(c[:, 1], np.roll(c[:, 0], 1)))
        if area < 25:
            continue
        pts = np.stack([c[:, 1] - 2 + 0.5, c[:, 0] - 2 + 0.5], 1)
        segs = merge_segments(fit_closed(pts, np.full(len(pts), 0.6), 3.0, 70), 0.5)
        subs.append([np.round(b, 2) for b in segs])
    return subs
