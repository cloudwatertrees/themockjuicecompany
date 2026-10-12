"""probe4.py MODE : s1 with #396's path modified: rev (reverse all subpaths), rot (rotate main contour start by half),
order (main contour last)."""
import sys, numpy as np
from pbart import load, write, PShape
from pathio import path_str
SP = '/tmp/work/'
mode = sys.argv[1]; sh = load(SP + 'exp/scenes/s1'); s = sh[396]
def reverse(sub):
    pts = [np.asarray(sub[0])]; segs = sub[1:]
    # endpoints chain
    ends = [np.asarray(sub[0])] + [np.asarray(g[-1]) for g in segs]
    out = [ends[-1]]
    for k in range(len(segs) - 1, -1, -1):
        g = segs[k]
        if g[0] == 'L': out.append(('L', ends[k]))
        else: out.append(('C', np.asarray(g[2]), np.asarray(g[1]), ends[k]))
    return out
def rotate(sub, m):
    ends = [np.asarray(sub[0])] + [np.asarray(g[-1]) for g in sub[1:]]
    segs = sub[1:]
    # assume closed (last end == start); rotate segment list
    segs = segs[m:] + segs[:m]
    return [ends[m]] + segs
subs = s.subs
if mode == 'rev': subs = [reverse(u) for u in subs]
elif mode == 'rot': subs = [rotate(subs[0], (len(subs[0]) - 1) // 2)] + subs[1:]
elif mode == 'order': subs = subs[1:] + subs[:1]
line = s.line(); head = line[:line.index(' M')]
sh[396] = PShape(s.layer, head + ' ' + path_str(subs))
write(sh, SP + 'exp/probe')
