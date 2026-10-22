"""Quick score of a data dir via the Python model (matches iOS to ~0.3/255)."""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.metrics import structural_similarity
from skimage.color import rgb2lab, deltaE_ciede2000
import model
from art import load
SP = '/tmp/work/'
REF = np.asarray(Image.open(SP + 'ref/ref.png').convert('RGB')).astype(np.float64) / 255
def luma(x): return x @ np.array([0.2126, 0.7152, 0.0722])
def lp(x, s): return np.stack([ndi.gaussian_filter(x[..., c], s) for c in range(3)], -1)
def score(P, ref=REF):
    s = structural_similarity(luma(P), luma(ref), data_range=1, gaussian_weights=True, sigma=1.5, use_sample_covariance=False)
    de = deltaE_ciede2000(rgb2lab(P), rgb2lab(ref)); dl = deltaE_ciede2000(rgb2lab(lp(P, 2)), rgb2lab(lp(ref, 2)))
    return s, de.mean(), np.percentile(de, 95), dl.mean(), np.percentile(dl, 95), dl.max()
def qscore(d, soft=True):
    P = model.render(load(d), d, soft)
    return P, score(P)
if __name__ == '__main__':
    for d in sys.argv[1:]:
        _, s = qscore(d)
        print('%-10s SSIM %.4f dE %.3f p95 %.2f | lp dE %.3f p95 %.2f max %.1f' % ((d.rstrip('/').split('/')[-1],) + s))
