import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity


def load(path, size=None):
    im = Image.open(path).convert('RGB')
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im).astype(np.float64)


def luma(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def ssim_map(a, b):
    """Wang et al. SSIM on luma: Gaussian window sigma 1.5, K1 0.01, K2 0.03."""
    s, m = structural_similarity(luma(a), luma(b), data_range=255, gaussian_weights=True,
                                 sigma=1.5, use_sample_covariance=False, full=True)
    return s, m


def scores(a, b):
    s, _ = ssim_map(a, b)
    srgb = structural_similarity(a, b, data_range=255, gaussian_weights=True, sigma=1.5,
                                 use_sample_covariance=False, channel_axis=2)
    mae = np.abs(a - b).mean((0, 1))
    return dict(ssim=s, ssim_rgb=srgb, mae=mae, mae_max=mae.max())


def fmt(d):
    return (f"SSIM(luma) {d['ssim']:.4f}  SSIM(RGB) {d['ssim_rgb']:.4f}  "
            f"MAE R/G/B {d['mae'][0]:.2f}/{d['mae'][1]:.2f}/{d['mae'][2]:.2f}")
