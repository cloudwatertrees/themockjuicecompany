"""Colour-class masks for the A/B scenes: the cream path and the brown earth banks along it."""
import os
import numpy as np
from scipy import ndimage as ndi
from colors import to_lab

# Input pixels per design unit (2 for the 2x upscaled sources); pixel sizes and morphology radii scale with it.
PX = float(os.environ.get("INPUT_SCALE", 1))


def path_mask(ref):
    lab = to_lab(ref)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    cream = (L > 80) & (A > -6) & (A < 12) & (B > 6) & (B < 32)
    cream = ndi.binary_opening(cream, iterations=round(2 * PX))
    lbl, n = ndi.label(cream)
    sizes = ndi.sum(cream, lbl, range(1, n + 1))
    path = np.isin(lbl, 1 + np.nonzero(sizes > 20000 * PX * PX)[0])
    return ndi.binary_fill_holes(path)


def border_mask(ref):
    """Brown earth banks: large brown components that touch the path."""
    lab = to_lab(ref)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    brown = (L > 28) & (L < 72) & (A > 5) & (A < 30) & (B > 8) & (B < 42)
    brown = ndi.binary_opening(brown, iterations=round(PX))
    lbl, n = ndi.label(brown)
    sizes = ndi.sum(brown, lbl, range(1, n + 1))
    near = ndi.binary_dilation(path_mask(ref), iterations=round(6 * PX))
    touch = ndi.sum(near, lbl, range(1, n + 1))
    border = np.isin(lbl, 1 + np.nonzero((sizes > 3000 * PX * PX) & (touch > 50 * PX * PX))[0])
    border = ndi.binary_closing(border, iterations=round(3 * PX))
    return ndi.binary_fill_holes(border) & ~path_mask(ref)
