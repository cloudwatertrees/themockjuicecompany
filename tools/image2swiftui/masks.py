"""Colour-class masks for the forest image: the cream path and its brown dirt borders."""
import numpy as np
from scipy import ndimage as ndi
from colors import to_lab


def path_mask(ref):
    lab = to_lab(ref)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    cream = (L > 72) & (A > -8) & (A < 12) & (B > 5) & (B < 40)
    cream = ndi.binary_opening(cream, iterations=2)
    lbl, n = ndi.label(cream)
    sizes = ndi.sum(cream, lbl, range(1, n + 1))
    path = np.isin(lbl, 1 + np.nonzero(sizes > 20000)[0])
    return ndi.binary_fill_holes(path)


def border_mask(ref):
    lab = to_lab(ref)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    brown = (L > 28) & (L < 70) & (A > 5) & (A < 30) & (B > 8) & (B < 42)
    brown = ndi.binary_opening(brown, iterations=1)
    lbl, n = ndi.label(brown)
    sizes = ndi.sum(brown, lbl, range(1, n + 1))
    border = np.isin(lbl, 1 + np.nonzero(sizes > 5000)[0])
    border = ndi.binary_closing(border, iterations=3)
    return ndi.binary_fill_holes(border) & ~path_mask(ref)
