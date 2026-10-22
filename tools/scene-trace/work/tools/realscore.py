"""SSIM (luma, sigma 1.5) and MAE of a real SwiftUI render against its source. usage: realscore.py RENDER.png REF.png"""
import sys, numpy as np
from PIL import Image
from skimage.metrics import structural_similarity
r = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(float) / 255
f = np.asarray(Image.open(sys.argv[2]).convert('RGB')).astype(float) / 255
l = lambda x: x @ np.array([0.2126, 0.7152, 0.0722])
s = structural_similarity(l(r), l(f), data_range=1, gaussian_weights=True, sigma=1.5, use_sample_covariance=False)
m = np.abs(r - f).mean((0, 1)) * 255
print(f'{sys.argv[1]}: real SSIM {s:.4f}  MAE {m[0]:.2f}/{m[1]:.2f}/{m[2]:.2f}')
