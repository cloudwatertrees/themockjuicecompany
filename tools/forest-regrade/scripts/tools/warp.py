"""Warp all layer data + soft zones by a registration field into the reference frame."""
import sys, os, numpy as np
from scipy import ndimage as ndi
from art import load, LAYERS, parse_path, rgb2hex
from pathio import path_str, map_subs
SP = '/tmp/work/'

def make_phi(field):
    fx, fy = field[..., 0].astype(np.float64), field[..., 1].astype(np.float64)
    H, W = fx.shape
    def phi(p):
        p = np.asarray(p, np.float64)
        c = [[np.clip(p[1] - 0.5, 0, H - 1)], [np.clip(p[0] - 0.5, 0, W - 1)]]
        return p + np.array([ndi.map_coordinates(fx, c, order=1)[0], ndi.map_coordinates(fy, c, order=1)[0]])
    return phi

def make_phi_vec(field):
    fx, fy = field[..., 0].astype(np.float64), field[..., 1].astype(np.float64)
    H, W = fx.shape
    def phi(P):
        P = np.asarray(P, np.float64)
        c = [np.clip(P[:, 1] - 0.5, 0, H - 1), np.clip(P[:, 0] - 0.5, 0, W - 1)]
        return P + np.stack([ndi.map_coordinates(fx, c, order=1), ndi.map_coordinates(fy, c, order=1)], 1)
    return phi

def snap(P, W):
    """Points on/outside the old canvas border stay at least as far outside after warping."""
    W = W.copy()
    lo = P <= 0; W[lo] = np.minimum(W[lo], P[lo])
    hx = P[:, 0] >= 937; W[hx, 0] = np.maximum(W[hx, 0], P[hx, 0])
    hy = P[:, 1] >= 1678; W[hy, 1] = np.maximum(W[hy, 1], P[hy, 1])
    return W

def warp_subs(subs, phiv):
    pts = []
    for seg in subs:
        pts.append(seg[0])
        for s in seg[1:]: pts.extend(s[1:])
    P = np.array(pts); W = snap(P, phiv(P)); it = iter(W)
    return map_subs(subs, lambda p: next(it))

if __name__ == '__main__':
    field = np.load(sys.argv[1]); src = sys.argv[2]; dst = sys.argv[3]
    os.makedirs(dst, exist_ok=True)
    phiv = make_phi_vec(field)
    for L in LAYERS + ['softZoneData']:
        out = []
        for line in open(os.path.join(src, L + '.txt')).read().split('\n'):
            line = line.strip()
            if not line: continue
            if L == 'softZoneData':
                out.append(path_str(warp_subs(parse_path(line), phiv))); continue
            toks = line.split(' ', 1); rest = toks[1]
            if rest.startswith('M'):
                out.append(toks[0] + ' ' + path_str(warp_subs(parse_path(rest), phiv)))
            else:
                f = rest.split(' ', 5)
                e = phiv(np.array([[float(f[1]), float(f[2])], [float(f[3]), float(f[4])]]))
                out.append('%s %s %.1f %.1f %.1f %.1f %s' % (toks[0], f[0], e[0, 0], e[0, 1], e[1, 0], e[1, 1], path_str(warp_subs(parse_path(f[5]), phiv))))
        open(os.path.join(dst, L + '.txt'), 'w').write('\n'.join(out) + '\n')
    print('warped ->', dst)
