"""Full views: extension alone at SCALE, and live+extension stacked (scroll order) at SCALE2.
python fullview.py [rebuild] [scale] """
import sys, time
import numpy as np
from common import *
from extdata import load_ext_layers
t0 = time.time()
ext = load_ext_layers(rebuild='rebuild' in sys.argv)
sc = float([a for a in sys.argv[1:] if a[0].isdigit() or a[0] == '.'][0]) if any(a[0].isdigit() or a[0] == '.' for a in sys.argv[1:]) else 0.5
print('shapes', len(ext), 'build %.1fs' % (time.time() - t0))
e = render(ext, sc, (0, 0, W, H))
save(e, SCRATCH / 'ext_full.png')
l = render(load_live_layers(), sc, (0, 0, W, H))
save(np.concatenate([l, e], 0), SCRATCH / 'stack_full.png')
print('done %.1fs' % (time.time() - t0))
