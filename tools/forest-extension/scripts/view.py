"""Crop views of the live art (or extension data) for visual study.

usage: python view.py OUT.png x0,y0,x1,y1 SCALE [layers=a,b] [ids] [src=live|ext|both] [alone]
  ids    : second panel with the selected layers' shapes in distinct flat colours over the normal render
  alone  : render only the selected layers (default: all layers, so the layers beneath are present)
  src    : 'ext' renders the extension data (y in extension space), 'both' stacks live + ext (y in 0..3356)
"""
import sys
import numpy as np
from common import *


def load(src):
    if src == 'live':
        return load_live_layers()
    from extdata import load_ext_layers
    ext = load_ext_layers()
    if src == 'ext':
        return ext
    return load_live_layers() + [shift(s, H) for s in ext]


def shift(s, dy):
    from extdata import translate
    return translate(s, 0, dy)


if __name__ == '__main__':
    out, box, sc = sys.argv[1], tuple(float(v) for v in sys.argv[2].split(',')), float(sys.argv[3])
    opts = dict(a.split('=', 1) if '=' in a else (a, True) for a in sys.argv[4:])
    shapes = in_box(load(opts.get('src', 'live')), box, 4)
    sel = opts.get('layers')
    sel = sel.split(',') if sel else None
    base = [s for s in shapes if sel is None or s.layer in sel] if 'alone' in opts else shapes
    panels = [render(base, sc, box)]
    if 'ids' in opts:
        pick = [s for s in shapes if sel is None or s.layer in sel]
        under = [] if 'alone' in opts else [s for s in shapes if s not in pick and LAYERS.index(s.layer) < min(LAYERS.index(p.layer) for p in pick)] if pick else shapes
        panels.append(render(under + ids_view(pick), sc, box))
    save(np.concatenate(panels, 1), out)
    print(out, panels[0].shape[1::-1], len(base), 'shapes')
