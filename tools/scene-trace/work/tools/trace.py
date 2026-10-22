"""Trace binary masks with potrace into design-space subpaths."""
import os, re, subprocess, tempfile, numpy as np
from scipy import ndimage as ndi

def write_pbm(mask, path):
    h, w = mask.shape
    packed = np.packbits(mask.astype(np.uint8), axis=1)
    with open(path, 'wb') as f:
        f.write(b'P4\n%d %d\n' % (w, h)); f.write(packed.tobytes())

def upsample_mask(mask, U, sigma=0.6):
    """Binary 1x mask -> smooth-boundary U-times mask (Gaussian pre-smoothing + bicubic zoom, threshold 0.5)."""
    m = ndi.gaussian_filter(mask.astype(np.float64), sigma, mode='constant')
    z = ndi.zoom(m, U, order=3, mode='grid-constant', grid_mode=True)
    return z > 0.5

def trace(mask_hr, U, x0, y0, turd=4, alphamax=1.0, opt=0.4):
    """mask_hr: bool array at U px per design unit, whose top-left is design point (x0, y0)."""
    if not mask_hr.any(): return []
    h, w = mask_hr.shape
    d = tempfile.mkdtemp()
    pbm, svg = os.path.join(d, 'm.pbm'), os.path.join(d, 'm.svg')
    write_pbm(mask_hr, pbm)
    subprocess.run(['potrace', '-s', '-t', str(turd), '-a', str(alphamax), '-O', str(opt), '-u', '20', '-o', svg, pbm], check=True)
    txt = open(svg).read()
    os.remove(pbm); os.remove(svg); os.rmdir(d)
    m = re.search(r'translate\(([-\d.]+),([-\d.]+)\) scale\(([-\d.]+),([-\d.]+)\)', txt)
    tx, ty, sx, sy = map(float, m.groups())
    subs = []
    for dstr in re.findall(r'\sd="([^"]+)"', txt):
        toks = re.findall(r'[MmCcLlZz]|-?\d+(?:\.\d+)?', dstr)
        i = 0; cur = np.zeros(2); start = np.zeros(2); seg = None; cmd = None
        def num():
            nonlocal i
            v = float(toks[i]); i += 1; return v
        def conv(p):
            return np.array([x0 + (tx + sx * p[0]) / U, y0 + (ty + sy * p[1]) / U])
        while i < len(toks):
            if re.match(r'[MmCcLlZz]', toks[i]):
                cmd = toks[i]; i += 1
                if cmd in 'Zz':
                    cur = start.copy(); continue
            if cmd in 'Mm':
                p = np.array([num(), num()]); cur = p + (cur if cmd == 'm' else 0); start = cur.copy()
                seg = [conv(cur)]; subs.append(seg); cmd = 'l' if cmd == 'm' else 'L'
            elif cmd in 'Cc':
                o = cur if cmd == 'c' else np.zeros(2)
                c1 = o + np.array([num(), num()]); c2 = o + np.array([num(), num()]); p = o + np.array([num(), num()])
                seg.append(('C', conv(c1), conv(c2), conv(p))); cur = p
            elif cmd in 'Ll':
                p = (cur if cmd == 'l' else 0) + np.array([num(), num()])
                seg.append(('L', conv(p))); cur = p
    return subs
