"""Seam view: live art bottom strip stacked on the extension's top strip, exactly as the scroll view joins them
(segments rasterised separately). usage: python seamview.py OUT.png [x0,x1] [above] [below] [scale] [rebuild]"""
import sys
import numpy as np
from common import *
from extdata import load_ext_layers
args = sys.argv[1:]
out = args[0]
x0, x1 = (float(v) for v in (args[1] if len(args) > 1 else '0,937').split(','))
above = float(args[2]) if len(args) > 2 else 150
below = float(args[3]) if len(args) > 3 else 300
sc = float(args[4]) if len(args) > 4 else 1.5
ext = load_ext_layers(rebuild='rebuild' in args)
live = load_live_layers()
a = render(in_box(live, (x0, H - above, x1, H), 4), sc, (x0, H - above, x1, H))
b = render(in_box(ext, (x0, 0, x1, below), 4), sc, (x0, 0, x1, below))
save(np.concatenate([a, b], 0), out)
print(out, a.shape[1], 'x', a.shape[0] + b.shape[0])
