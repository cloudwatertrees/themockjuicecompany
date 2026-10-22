"""Detail and edge fidelity of a trace against its source, with the Python copy of the iOS renderer.

usage: qmetrics.py SRC.png DATADIR [TAG]
Prints, at design scale 1x:
  SSIM      luma SSIM (sigma 1.5)
  edgeF1    Canny edges (luma, sigma 1) of render vs source, matched within 1 px: F1 (recall / precision)
  detail    high-frequency energy (Laplacian of Gaussian, sigma 0.7) of render / source, outside the cream path;
            1.0 = as much fine texture as the source, below 1 = flattened
  gradSSIM  SSIM of the gradient-magnitude maps (structure of edges and strokes)
Writes DATADIR/../render_1x.png and DATADIR/../render_phone.png (phone scale 2556/1678)."""
import os
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.feature import canny
from skimage.metrics import structural_similarity

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work', 'tools'))
from pbart import load  # noqa: E402
from pbrender import render  # noqa: E402

src, d = sys.argv[1], sys.argv[2]
tag = sys.argv[3] if len(sys.argv) > 3 else os.path.basename(os.path.dirname(d.rstrip('/')))
ref = np.asarray(Image.open(src).convert('RGB')).astype(np.float64) / 255
H, W = ref.shape[:2]
shapes = load(d)
k = W / 937                                   # source pixels per design unit (data is in design units)
img = np.clip(render(shapes, k, 0, 0, W, H), 0, 1)
out = os.path.dirname(d.rstrip('/'))
Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(os.path.join(out, 'render_1x.png'))
s = 2556 / 1678
ph = np.clip(render(shapes, s, 0, 0, round(W / k * s), round(H / k * s)), 0, 1)
Image.fromarray((ph * 255 + 0.5).astype(np.uint8)).save(os.path.join(out, 'render_phone.png'))

lum = lambda x: x @ np.array([0.2126, 0.7152, 0.0722])
lr, lf = lum(img), lum(ref)
ssim = structural_similarity(lr, lf, data_range=1, gaussian_weights=True, sigma=1.5, use_sample_covariance=False)
er, ef = canny(lr, sigma=1.0), canny(lf, sigma=1.0)
near = lambda e: ndi.binary_dilation(e, iterations=1)
rec = (ef & near(er)).sum() / max(ef.sum(), 1)
pre = (er & near(ef)).sum() / max(er.sum(), 1)
f1 = 2 * rec * pre / max(rec + pre, 1e-9)
cream = (ref[..., 0] > 0.84) & (ref[..., 1] > 0.76) & (ref[..., 2] > 0.63)
mask = ~ndi.binary_dilation(cream, iterations=3)
hr, hf = ndi.gaussian_laplace(lr, 0.7), ndi.gaussian_laplace(lf, 0.7)
detail = np.sqrt((hr[mask] ** 2).mean() / (hf[mask] ** 2).mean())
g = lambda x: np.hypot(ndi.sobel(x, 0), ndi.sobel(x, 1))
gs = structural_similarity(g(lr), g(lf), data_range=float(g(lf).max()), gaussian_weights=True, sigma=1.5, use_sample_covariance=False)
print(f'{tag:10s} SSIM {ssim:.4f}  edgeF1 {f1:.3f} (rec {rec:.3f} pre {pre:.3f})  detail {detail:.3f}  gradSSIM {gs:.4f}  shapes {len(shapes)}')


def shape_fidelity(ref, img, name, sel):
    """Boundary error (mean px distance, both directions) and wobble ratio of one object class's mask."""
    from skimage import measure
    a, b = sel(ref), sel(img)
    a = ndi.binary_opening(a, iterations=1); b = ndi.binary_opening(b, iterations=1)
    ea = a ^ ndi.binary_erosion(a); eb = b ^ ndi.binary_erosion(b)
    if ea.sum() == 0 or eb.sum() == 0:
        return f'{name}: n/a'
    da, db = ndi.distance_transform_edt(~ea), ndi.distance_transform_edt(~eb)
    berr = 0.5 * (da[eb].mean() + db[ea].mean())

    def wobble(m):
        r = []
        for c in measure.find_contours(ndi.gaussian_filter(m.astype(float), 0.7), 0.5):
            if len(c) < 80:
                continue
            sm = np.stack([ndi.gaussian_filter1d(c[:, k], 6, mode='wrap') for k in range(2)], 1)
            r.append(np.linalg.norm(c - sm, axis=1))
        return np.concatenate(r).mean() if r else np.nan
    return f'{name}: boundary err {berr:.2f} px, wobble {wobble(b):.3f} (source {wobble(a):.3f})'


path_sel = lambda x: (x[..., 0] > 0.84) & (x[..., 1] > 0.76) & (x[..., 2] > 0.63) & (x[..., 0] - x[..., 2] < 0.3)
cap_sel = lambda x: (x[..., 0] > 0.6) & (x[..., 0] - x[..., 1] > 0.25) & (x[..., 0] - x[..., 2] > 0.2)
print(' ' * 11 + shape_fidelity(ref, img, 'path', path_sel) + ' | ' + shape_fidelity(ref, img, 'caps', cap_sel))
