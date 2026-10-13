"""Split the merged bell-tree groups (backTrees, frontTrees) into individual trees with hand-set seeds.
Seed = (name, layer, apex x, apex y, bottom y, half width at bottom), read off grid views of the layers."""
import numpy as np
from fe.core import *

SEEDS = [('B1', 'backTrees', 45, -30, 110, 75), ('B2', 'backTrees', 150, -40, 60, 55), ('B3', 'backTrees', 205, 27, 235, 80),
         ('B4', 'backTrees', 73, 77, 318, 100), ('B5', 'backTrees', 15, 550, 835, 90),
         ('F1', 'frontTrees', 15, 1115, 1515, 75), ('F2', 'frontTrees', 160, 1220, 1465, 70), ('F3', 'frontTrees', 60, 1280, 1560, 95),
         ('R1', 'frontTrees', 700, 1052, 1245, 75), ('R2', 'frontTrees', 905, 945, 1160, 70), ('R3', 'frontTrees', 825, 1085, 1300, 80),
         ('R4', 'frontTrees', 835, 1225, 1460, 95), ('R5', 'frontTrees', 915, 1345, 1682, 100)]

def is_ground(lab):
    """Olive / yellow-green ground under the trees (not foliage): b* high relative to a*, foliage is a* < -18 & b* < 30."""
    return lab[2] > 27 and lab[1] > -17

def split(C):
    S = C.shapes
    trees = {s[0]: [] for s in SEEDS}; ground = {'backTrees': [], 'frontTrees': []}; rest = []
    for k, s in enumerate(S):
        if s.layer not in ('backTrees', 'frontTrees'): continue
        m = C.top == k
        if m.sum() == 0:
            b = tbox(s); cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2; lab = rgb2lab(mean_rgb(s))
        else:
            yy, xx = np.nonzero(m); cx, cy = C.to_units(yy.mean(), xx.mean()); lab = C.lab[m].mean(0)
        if is_ground(lab): ground[s.layer].append(k); continue
        best, bs = None, 1.3
        for name, L, ax, ay, yb, hw in SEEDS:
            if L != s.layer or not (ay - 10 <= cy <= yb + 10): continue
            hwy = 15 + hw * np.clip((cy - ay) / (yb - ay), 0.2, 1)
            sc = abs(cx - ax) / hwy
            if sc < bs: best, bs = name, sc
        (trees[best] if best else rest).append(k)
    return trees, ground, rest
