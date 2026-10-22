"""Preview of the layer assignment: python classmap.py IMAGE OUT.png"""
import sys, numpy as np
from PIL import Image
from skimage.segmentation import felzenszwalb
from hf_groups import GROUPS, assign
from masks import border_mask
from metrics import load
ref = load(sys.argv[1])
fine = felzenszwalb(ref.astype(np.uint8), scale=5, sigma=0.3, min_size=3)
g = assign(ref, fine, border_mask(ref))[fine]
pal = np.array([(225, 235, 170), (150, 90, 50), (255, 240, 210), (60, 150, 255), (150, 140, 200), (110, 60, 20),
                (60, 200, 60), (0, 90, 70), (255, 0, 0), (255, 0, 255)], float)
vis = (pal[g] * 0.7 + ref * 0.3).astype(np.uint8)
Image.fromarray(vis).resize((ref.shape[1] // 2, ref.shape[0] // 2)).save(sys.argv[2])
print({n: round(float((g == i).mean()), 3) for i, n in enumerate(GROUPS)})
