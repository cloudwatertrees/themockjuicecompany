"""probe2.py N : scene s1 with N tiny separate dummy shapes drawn first (hidden under the base)."""
import sys
from pbart import load, write, PShape
SP = '/tmp/work/'
N = int(sys.argv[1]); sh = load(SP + 'exp/scenes/s1')
d = [PShape('meadow', '000000 M%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f Z' % (400 + (i % 20) * 4, 700 + (i // 20) * 4, 403 + (i % 20) * 4, 700 + (i // 20) * 4, 403 + (i % 20) * 4, 703 + (i // 20) * 4, 400 + (i % 20) * 4, 703 + (i // 20) * 4)) for i in range(N)]
write(d + sh, SP + 'exp/probe')
