"""probe.py K : scene s1 with a K-segment dummy path (drawn first, hidden under the base) -> data dir exp/probe"""
import sys, numpy as np
from pbart import load, write, PShape
SP = '/tmp/work/'
K = int(sys.argv[1]); kind = sys.argv[2] if len(sys.argv) > 2 else 'L'
sh = load(SP + 'exp/scenes/s1')
if K > 0:
    t = np.linspace(0, 2 * np.pi, K + 1)[:-1]
    pts = [(450 + 8 * np.cos(a), 800 + 8 * np.sin(a)) for a in t]
    if kind == 'L':
        p = 'M%.2f %.2f ' % pts[0] + ' '.join('L%.2f %.2f' % q for q in pts[1:]) + ' Z'
    else:
        p = 'M%.2f %.2f ' % pts[0] + ' '.join('C%.2f %.2f %.2f %.2f %.2f %.2f' % (q[0], q[1], q[0], q[1], q[0], q[1]) for q in pts[1:]) + ' Z'
    dummy = PShape('meadow', '000000 ' + p)
    sh = [dummy] + sh
write(sh, SP + 'exp/probe')
