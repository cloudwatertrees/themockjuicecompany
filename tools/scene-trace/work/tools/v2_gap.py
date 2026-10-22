"""v2: where the remaining SSIM / dE00 gap sits. Splits the loss between edge bands and flat interiors, and measures how
much of it is the render's edge sharpness vs the reference's softness (render blurred to the reference's edge spread),
and how much is reference texture a flat-fill vector cannot carry (reference vs its own edge-preserving smooth).
usage: v2_gap.py RENDER_1x.png REG.npy [LAYERMAP.npy]   (run from the working copy's tools/)"""
import sys, numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
from skimage.metrics import structural_similarity
from skimage.color import rgb2lab, deltaE_ciede2000
from quick import REF, luma, score

P = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(np.float64) / 255
reg = np.load(sys.argv[2])
_, smap = structural_similarity(luma(P), luma(REF), data_range=1, gaussian_weights=True, sigma=1.5,
                                use_sample_covariance=False, full=True)
de = deltaE_ciede2000(rgb2lab(P), rgb2lab(REF))
edge = np.zeros(reg.shape, bool)
edge[:, 1:] |= reg[:, 1:] != reg[:, :-1]; edge[1:] |= reg[1:] != reg[:-1]
for r in (1, 2, 3):
    band = ndi.binary_dilation(edge, iterations=r)
    loss = 1 - smap
    print('edge band r=%d: %.1f%% of px, %.1f%% of SSIM loss, %.1f%% of dE sum' %
          (r, 100 * band.mean(), 100 * loss[band].sum() / loss.sum(), 100 * de[band].sum() / de.sum()))
if len(sys.argv) > 3:
    from art import LAYERS
    lm = np.load(sys.argv[3]); loss = 1 - smap
    for i, n in enumerate(LAYERS):
        m = lm == i
        if m.any():
            print('%-10s %5.1f%% px  %5.1f%% SSIM loss  %5.1f%% dE sum  SSIM %.4f dE %.2f' % (n, 100 * m.mean(),
                  100 * loss[m].sum() / loss.sum(), 100 * de[m].sum() / de.sum(), smap[m].mean(), de[m].mean()))
# oracles: the render with the reference's own pixels in the edge band (perfect edges) or outside it (perfect fills)
for r in (1, 2):
    band = ndi.binary_dilation(edge, iterations=r)[..., None]
    print('oracle r=%d: perfect edges SSIM %.4f dE %.3f | perfect fills SSIM %.4f dE %.3f' %
          ((r,) + score(np.where(band, REF, P))[:2] + score(np.where(band, P, REF))[:2]))
# interior residual by scale: the render plus the residual low-passed at sigma (outside the edge band) - what fills
# smooth at that scale could still gain; the rest is finer texture
band = ndi.binary_dilation(edge, iterations=1)
res = REF - P; wt = (~band).astype(float)
for s in (1.0, 2.0, 4.0):
    lpres = np.stack([ndi.gaussian_filter(res[..., c] * wt, s) for c in range(3)], -1) / np.maximum(ndi.gaussian_filter(wt, s), 1e-3)[..., None]
    print('interior residual low-passed at sigma %.0f added: SSIM %.4f dE %.3f' % ((s,) + score(np.where(band[..., None], P, P + lpres))[:2]))
for s in (0.3, 0.45, 0.6):
    Pb = np.stack([ndi.gaussian_filter(P[..., c], s) for c in range(3)], -1)
    print('render blurred sigma %.2f: SSIM %.4f dE %.3f' % ((s,) + score(Pb)[:2]))
R8 = (REF * 255).astype(np.uint8)
for d, sc in ((5, 20), (7, 30)):
    Rs = cv2.bilateralFilter(R8, d, sc, sc).astype(np.float64) / 255
    print('reference vs its bilateral smooth (d %d, sigma %d): SSIM %.4f dE %.3f' % ((d, sc) + score(Rs)[:2]))
