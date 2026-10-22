"""Where SSIM is lost: per-layer-class mean SSIM and share of the total loss. usage: ssimmap.py RENDER.png REF.png"""
import sys, numpy as np
from PIL import Image
from skimage.metrics import structural_similarity
sys.path.insert(0, '../../i2s')
from skimage.segmentation import felzenszwalb
from hf_groups import GROUPS, assign
from masks import border_mask
ren = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(float); ref = np.asarray(Image.open(sys.argv[2]).convert('RGB')).astype(float)
l = lambda x: x @ np.array([0.2126, 0.7152, 0.0722]) / 255
_, m = structural_similarity(l(ren), l(ref), data_range=1, gaussian_weights=True, sigma=1.5, use_sample_covariance=False, full=True)
fine = felzenszwalb(ref.astype(np.uint8), scale=5, sigma=0.3, min_size=3)
g = assign(ref, fine, border_mask(ref))[fine]
loss = 1 - m
print('mean SSIM %.4f' % m.mean())
for i, n in enumerate(GROUPS):
    k = g == i
    if k.any(): print(f'{n:10s} area {k.mean():.3f}  SSIM {m[k].mean():.4f}  loss share {loss[k].sum() / loss.sum():.3f}')
