"""Score per-layer data against its source with the Python copy of the iOS renderer.
usage: sscore.py DATADIR REF.png [--dev]
Design space 1x (W x H of REF); --dev also renders the 393x852 @3x phone framing (aspect-fill, centred).
SSIM on luma (Rec. 709, Gaussian sigma 1.5, as score.py), MAE per channel (0-255)."""
import sys, numpy as np
from PIL import Image
from skimage.metrics import structural_similarity
from pbart import load
from pbrender import render

def luma(x): return x @ np.array([0.2126, 0.7152, 0.0722])

def ssim(a, b):
    return structural_similarity(luma(a), luma(b), data_range=1, gaussian_weights=True, sigma=1.5, use_sample_covariance=False)

d, refp = sys.argv[1], sys.argv[2]
ref = np.asarray(Image.open(refp).convert('RGB')).astype(np.float64) / 255
H, W = ref.shape[:2]
shapes = load(d)
img = np.clip(render(shapes, 1.0, 0, 0, W, H), 0, 1)
Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(d.rstrip('/') + '_py1x.png')
mae = np.abs(img - ref).mean((0, 1)) * 255
print(f'{d}: 1x SSIM {ssim(img, ref):.4f}  MAE {mae[0]:.2f}/{mae[1]:.2f}/{mae[2]:.2f}  shapes {len(shapes)}')
if '--dev' in sys.argv:
    from scipy import ndimage as ndi
    s = 2556 / H; ox = (1179 - W * s) / 2
    dev = np.clip(render(shapes, s, ox, 0, 1179, 2556), 0, 1)
    yy, xx = np.mgrid[0:2556, 0:1179]
    sx = (xx + 0.5 - ox) / s - 0.5; sy = (yy + 0.5) / s - 0.5
    rd = np.stack([ndi.map_coordinates(ref[..., c], [sy, sx], order=3, mode='nearest') for c in range(3)], -1).clip(0, 1)
    Image.fromarray((dev * 255 + 0.5).astype(np.uint8)).save(d.rstrip('/') + '_pydev.png')
    print(f'{d}: dev3x SSIM {ssim(dev, rd):.4f}')
