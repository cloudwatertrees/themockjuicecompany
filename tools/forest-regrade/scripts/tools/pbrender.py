"""Python render model for Phase B data (flat/mesh fills, optional blur groups), any scale/offset."""
import sys, numpy as np
from scipy import ndimage as ndi
from PIL import Image
from art import flatten, rasterize, W, H
from pbart import load, bilinear_dense

def render(shapes, scale=1.0, ox=0.0, oy=0.0, Wp=W, Hp=H, S=16):
    img = np.zeros((Hp, Wp, 3)); T = None
    covs = None if not any(sh.blur > 0 for sh in shapes) else [rasterize(flatten(sh.subs, scale), scale, ox, oy, Wp, Hp, S) for sh in shapes]
    if covs is None:      # no blurred groups: stream shape by shape (low memory)
        for sh in shapes:
            composite_one(img, None, sh, rasterize(flatten(sh.subs, scale), scale, ox, oy, Wp, Hp, S), scale, ox, oy, premult=False)
        return img
    # source-over in order; blurred groups: consecutive shapes with the same blur in the same layer
    i = 0
    while i < len(shapes):
        sh = shapes[i]
        if sh.blur > 0:
            j = i
            while j < len(shapes) and shapes[j].blur == sh.blur and shapes[j].layer == sh.layer: j += 1
            lay = np.zeros((Hp, Wp, 3)); la = np.zeros((Hp, Wp))
            for k in range(i, j):
                composite_one(lay, la, shapes[k], covs[k], scale, ox, oy)
            s = sh.blur * scale
            lay = np.stack([ndi.gaussian_filter(lay[..., c], s, mode='constant') for c in range(3)], -1); la = ndi.gaussian_filter(la, s, mode='constant')
            img = img * (1 - la[..., None]) + lay
            i = j; continue
        composite_one(img, None, sh, covs[i], scale, ox, oy, premult=False)
        i += 1
    return img

def composite_one(img, alpha, sh, cov, scale, ox, oy, premult=True):
    if cov is None: return
    x0, y0, c = cov; h, w = c.shape
    ys, xs = np.mgrid[y0:y0 + h, x0:x0 + w]
    col = sh.colour_at((xs + 0.5 - ox) / scale, (ys + 0.5 - oy) / scale)
    a = c[..., None]
    img[y0:y0 + h, x0:x0 + w] = img[y0:y0 + h, x0:x0 + w] * (1 - a) + col * a
    if alpha is not None: alpha[y0:y0 + h, x0:x0 + w] = alpha[y0:y0 + h, x0:x0 + w] * (1 - c) + c

if __name__ == '__main__':
    d, out = sys.argv[1], sys.argv[2]
    sc = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    box = [float(v) for v in sys.argv[4].split(',')] if len(sys.argv) > 4 else None
    shapes = load(d)
    if box:
        x0, y0, x1, y1 = box
        img = render(shapes, sc, -x0 * sc, -y0 * sc, int((x1 - x0) * sc), int((y1 - y0) * sc))
    else:
        img = render(shapes, sc, 0, 0, int(W * sc), int(H * sc))
    Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(out)
