"""probe3.py MODE N : s1 with N squares prepended, as one multi-subpath shape (MODE=one) or with N-seg squares (MODE=segs)."""
import sys
from pbart import load, write, PShape
SP = '/tmp/work/'
mode, N = sys.argv[1], int(sys.argv[2]); sh = load(SP + 'exp/scenes/s1')
sq = lambda i: 'M%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f Z' % (400 + (i % 20) * 4, 700 + (i // 20) * 4, 403 + (i % 20) * 4, 700 + (i // 20) * 4, 403 + (i % 20) * 4, 703 + (i // 20) * 4, 400 + (i % 20) * 4, 703 + (i // 20) * 4)
if mode == 'one':
    d = [PShape('meadow', '000000 ' + ' '.join(sq(i) for i in range(N)))]
elif mode == 'big':   # N separate draws, each a 40-segment polygon of radius 20 units
    import numpy as np
    d = []
    for i in range(N):
        t = np.linspace(0, 2 * np.pi, 41)[:-1]; cx, cy = 300 + (i % 10) * 45, 600 + (i // 10) * 45
        d.append(PShape('meadow', '000000 M%.2f %.2f ' % (cx + 20, cy) + ' '.join('L%.2f %.2f' % (cx + 20 * np.cos(a), cy + 20 * np.sin(a)) for a in t[1:]) + ' Z'))
write(d + sh, SP + 'exp/probe')
