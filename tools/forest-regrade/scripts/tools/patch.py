"""Re-segment + re-trace areas where the fitted render still differs from the reference.
Residual spots -> reference segments (Felzenszwalb) clipped to the spot -> potrace at 4x -> new shapes
appended on top of the topmost layer there. Colours come from the subsequent joint refit."""
import sys, os, shutil, numpy as np
from scipy import ndimage as ndi
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000
from skimage.segmentation import felzenszwalb
from art import LAYERS, rgb2hex, load
from pathio import path_str
from trace import upsample_mask, trace
from score import labelmap
SP = '/tmp/work/'

def border_band(field, margin=2):
    """Pixels between the canvas edge and the warped old canvas edge (stretched by border snapping)."""
    H, W = field.shape[:2]
    band = np.zeros((H, W), bool)
    yy, xx = np.mgrid[0:H, 0:W]
    dxl = np.maximum(field[:, 0, 0], 0); band |= xx < (dxl[:, None] + margin) * (dxl[:, None] > 0.3)
    dxr = np.minimum(field[:, -1, 0], 0); band |= xx >= W + (dxr[:, None] - margin) * (dxr[:, None] < -0.3)
    dyt = np.maximum(field[0, :, 1], 0); band |= yy < (dyt[None, :] + margin) * (dyt[None, :] > 0.3)
    dyb = np.minimum(field[-1, :, 1], 0); band |= yy >= H + (dyb[None, :] - margin) * (dyb[None, :] < -0.3)
    return band

def run(src, render, dst, thr=2.5, min_area=8, U=4, fz_scale=60, force=None):
    ref = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
    ren = np.asarray(Image.open(render).convert('RGB')).astype(np.float64) / 255
    lp = lambda x: np.stack([ndi.gaussian_filter(x[..., c], 1.0) for c in range(3)], -1)
    d = deltaE_ciede2000(rgb2lab(lp(ren)), rgb2lab(lp(ref)))
    lab = labelmap(src)
    seed = d > thr
    if force is not None:
        seed |= force; d = np.where(force, np.maximum(d, 2 * thr), d)
    comp, n = ndi.label(seed)
    sizes = ndi.sum(np.ones_like(d), comp, range(1, n + 1))
    objs = ndi.find_objects(comp)
    H, W = d.shape
    done = np.zeros((H, W), bool)
    new = {L: [] for L in LAYERS}
    npatch = 0
    for k in np.argsort(-sizes):
        if sizes[k] < min_area: break
        sl = objs[k]
        y0, y1 = max(sl[0].start - 10, 0), min(sl[0].stop + 10, H)
        x0, x1 = max(sl[1].start - 10, 0), min(sl[1].stop + 10, W)
        spot = ndi.binary_dilation(comp[y0:y1, x0:x1] == k + 1, iterations=2) & ~done[y0:y1, x0:x1]
        if spot.sum() < min_area: continue
        seg = felzenszwalb(ref[y0:y1, x0:x1], scale=fz_scale, sigma=0.5, min_size=6)
        for s in np.unique(seg[spot]):
            full = seg == s
            piece = full & spot
            if piece.sum() < 4: continue
            # small segments are traced whole so their real outline is kept
            region = full if full.sum() <= 3 * piece.sum() else piece
            region = region & ~done[y0:y1, x0:x1]
            if region.sum() < 4 or d[y0:y1, x0:x1][region].mean() < thr * 0.6: continue
            m1 = np.zeros((y1 - y0 + 4, x1 - x0 + 4), bool); m1[2:-2, 2:-2] = region
            subs = trace(upsample_mask(m1, U), U, x0 - 2, y0 - 2)
            if not subs: continue
            labs = lab[y0:y1, x0:x1][region]; labs = labs[labs >= 0]
            L = LAYERS[np.bincount(labs).argmax()] if len(labs) else 'meadow'
            col = ref[y0:y1, x0:x1][region].mean(0)
            new[L].append('%s %s' % (rgb2hex(col), path_str(subs)))
            done[y0:y1, x0:x1] |= region
            npatch += 1
    os.makedirs(dst, exist_ok=True)
    for L in LAYERS:
        lines = [l for l in open(os.path.join(src, L + '.txt')).read().split('\n') if l.strip()]
        open(os.path.join(dst, L + '.txt'), 'w').write('\n'.join(lines + new[L]) + '\n')
    shutil.copy(os.path.join(src, 'softZoneData.txt'), dst)
    print('patches:', npatch, {L: len(v) for L, v in new.items() if v}, 'px', done.sum())

if __name__ == '__main__':
    force = border_band(np.load(sys.argv[4])) if len(sys.argv) > 4 else None
    thr = float(sys.argv[5]) if len(sys.argv) > 5 else 2.5
    run(sys.argv[1], sys.argv[2], sys.argv[3], thr=thr, force=force)
