"""Re-segment + re-trace mismatch areas (and forced border bands) from the reference.
Border-touching patches are extended off-canvas by edge replication so the soft-pass blur sees a natural continuation."""
import sys, os, shutil, numpy as np
from scipy import ndimage as ndi
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000
from skimage.segmentation import felzenszwalb
from art import LAYERS, rgb2hex, W, H
from pathio import path_str
from trace import upsample_mask, trace
from score import labelmap
from patch import border_band
SP = '/tmp/work/'
EXT = 12

def band_chunks(band, L=64):
    """Split the border band into chunks along each edge."""
    out = []
    for side in ('l', 'r', 't', 'b'):
        m = np.zeros_like(band)
        if side == 'l': m[:, :W // 2] = band[:, :W // 2]; m[:60] = m[-60:] = False
        if side == 'r': m[:, W // 2:] = band[:, W // 2:]; m[:60] = m[-60:] = False
        if side == 't': m[:H // 2] = band[:H // 2]
        if side == 'b': m[H // 2:] = band[H // 2:]
        if side in 'lr': m &= ~(np.arange(H)[:, None] < 60) & ~(np.arange(H)[:, None] >= H - 60)
        if not m.any(): continue
        if side in 'lr':
            for y in range(0, H, L):
                c = np.zeros_like(m); c[y:y + L] = m[y:y + L]
                if c.any(): out.append(c)
        else:
            for x in range(0, W, L):
                c = np.zeros_like(m); c[:, x:x + L] = m[:, x:x + L]
                if c.any(): out.append(c)
    return out

def trace_region(region, x0, y0, U=4):
    """region: bool mask whose top-left pixel is design (x0, y0). Extends off-canvas where it touches the canvas edge."""
    h, w = region.shape
    pl = EXT if x0 == 0 and region[:, 0].any() else 0
    pr = EXT if x0 + w == W and region[:, -1].any() else 0
    pt = EXT if y0 == 0 and region[0].any() else 0
    pb = EXT if y0 + h == H and region[-1].any() else 0
    r = np.pad(region, ((pt, pb), (pl, pr)), mode='edge')
    r = np.pad(r, 2)
    return trace(upsample_mask(r, U), U, x0 - pl - 2, y0 - pt - 2)

def run(src, render, dst, field=None, thr=2.5, min_area=8, fz_scale=60):
    ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
    ren = np.asarray(Image.open(render).convert('RGB')).astype(np.float64) / 255
    lp = lambda x: np.stack([ndi.gaussian_filter(x[..., c], 1.0) for c in range(3)], -1)
    d = deltaE_ciede2000(rgb2lab(lp(ren)), rgb2lab(lp(ref)))
    lab = labelmap(src)
    band = border_band(field) if field is not None else np.zeros((H, W), bool)
    jobs = [(c, True) for c in band_chunks(band)]
    comp, n = ndi.label((d > thr) & ~band)
    sizes = ndi.sum(np.ones_like(d), comp, range(1, n + 1))
    for k in np.argsort(-sizes):
        if sizes[k] < min_area: break
        jobs.append((comp == k + 1, False))
    done = np.zeros((H, W), bool); new = {L: [] for L in LAYERS}; npatch = 0
    for mask, forced in jobs:
        ys, xs = np.nonzero(mask)
        mg = 16 if forced else 10
        y0, y1 = max(ys.min() - mg, 0), min(ys.max() + 1 + mg, H)
        x0, x1 = max(xs.min() - mg, 0), min(xs.max() + 1 + mg, W)
        spot = ndi.binary_dilation(mask[y0:y1, x0:x1], iterations=3 if forced else 2) & ~done[y0:y1, x0:x1]
        if spot.sum() < 4: continue
        seg = felzenszwalb(ref[y0:y1, x0:x1], scale=fz_scale, sigma=0.5, min_size=6)
        for s in np.unique(seg[spot]):
            full = seg == s
            piece = full & spot
            if piece.sum() < 4: continue
            region = (full if full.sum() <= 3 * piece.sum() else piece) & ~done[y0:y1, x0:x1]
            if region.sum() < 4: continue
            if not forced and d[y0:y1, x0:x1][region].mean() < thr * 0.6: continue
            subs = trace_region(region, x0, y0)
            if not subs: continue
            labs = lab[y0:y1, x0:x1][region]; labs = labs[labs >= 0]
            L = LAYERS[np.bincount(labs).argmax()] if len(labs) else 'meadow'
            new[L].append('%s %s' % (rgb2hex(ref[y0:y1, x0:x1][region].mean(0)), path_str(subs)))
            done[y0:y1, x0:x1] |= region; npatch += 1
    os.makedirs(dst, exist_ok=True)
    for L in LAYERS:
        lines = [l for l in open(os.path.join(src, L + '.txt')).read().split('\n') if l.strip()]
        open(os.path.join(dst, L + '.txt'), 'w').write('\n'.join(lines + new[L]) + '\n')
    shutil.copy(os.path.join(src, 'softZoneData.txt'), dst)
    print('patches:', npatch, 'px', done.sum(), {L: len(v) for L, v in new.items() if v})

if __name__ == '__main__':
    f = np.load(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] != '-' else None
    run(sys.argv[1], sys.argv[2], sys.argv[3], f, float(sys.argv[5]) if len(sys.argv) > 5 else 2.5)
