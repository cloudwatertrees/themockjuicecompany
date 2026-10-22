"""Extension data access for viewers: builds the scene (or loads the cached data files) and translates shapes."""
import os
from common import SCRATCH, EXT, LAYERS
from pbart import PShape, load as pload, write as pwrite
from art import parse_path

DATA = SCRATCH / 'ext_data'


def build_and_cache():
    import scene
    layers, pm, pe = scene.build()
    shapes = [s for L in LAYERS for s in layers.get(L, [])]
    pwrite(shapes, str(DATA))
    return shapes


def load_ext_layers(rebuild=False):
    if rebuild or not (DATA / 'meadow.txt').exists():
        return build_and_cache()
    return pload(str(DATA))


def translate(s, dx, dy):
    """Copy of a PShape moved by (dx, dy): path coordinates (absolute M/L/C only change; relative l/c stay)."""
    import re
    toks = re.findall(r'[MLCZlc]|-?\d+(?:\.\d+)?|-?\.\d+', s.pathstr)
    out = []; cmd = None; k = 0
    for t in toks:
        if t in 'MLCZlc':
            cmd = t; k = 0; out.append(t); continue
        v = float(t)
        if cmd in 'MLC':
            v += dx if k % 2 == 0 else dy
        k += 1
        out.append('%g' % v)
    ps = ' '.join(out)
    return PShape(s.layer, pathstr=ps, cols=s.cols, nx=s.nx, ny=s.ny)
