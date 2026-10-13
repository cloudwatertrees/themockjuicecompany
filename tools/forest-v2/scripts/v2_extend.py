"""v2: start a taller (phone-shaped) reference from the traced 937x1678 one. The new image is resized to width 937, the
old reference is located inside it (normalised cross-correlation), the old per-pixel layer map is placed at that
offset, and the new strips above and below get layers by nearest layer colour (Lab, from the old map) plus the flower
colour masks. Writes the new ref.png and layermap; then run v2_regions.py onwards as in README.md.
usage: v2_extend.py NEW_IMAGE OLD_REF.png OLD_LAYERMAP.npy OUT_REF.png OUT_LAYERMAP.npy"""
import sys, numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2lab

new_p, old_p, lm_p, out_ref, out_lm = sys.argv[1:6]
old = np.asarray(Image.open(old_p).convert('RGB')); lm = np.load(lm_p)
H0, W0 = old.shape[:2]
im = Image.open(new_p).convert('RGB')
if im.width != W0:
    im = im.resize((W0, round(im.height * W0 / im.width)), Image.LANCZOS)
new = np.asarray(im); H1 = new.shape[0]
print('new reference %dx%d (aspect %.4f; iPhone 16 Pro 0.4600)' % (W0, H1, W0 / H1))
assert H1 >= H0, 'new image is not taller than the old one at the same width'
# locate the old scene in the new image (vertical offset; columns must line up after the resize)
res = cv2.matchTemplate(cv2.cvtColor(new, cv2.COLOR_RGB2GRAY), cv2.cvtColor(old, cv2.COLOR_RGB2GRAY), cv2.TM_CCOEFF_NORMED)
_, score, _, (ox, oy) = cv2.minMaxLoc(res)
print('old scene found at x %d y %d, match %.3f (below ~0.9: content was redrawn, check the layer map preview)' % (ox, oy, score))
d = np.abs(new[oy:oy + H0, ox:ox + W0].astype(int) - old.astype(int)).mean()
print('mean abs difference in the overlap %.2f/255' % d)
out = np.full((H1, W0), -1, np.int16)
out[oy:oy + H0, ox:ox + W0] = lm
# strips: nearest layer colour, then a 9x9 majority to keep it coarse (layers are semantic, not exact)
nl = rgb2lab(new / 255.0); ol = rgb2lab(old / 255.0)
from art import LAYERS
keep = ['meadow', 'hedge', 'pathEdges', 'path', 'backTrees', 'pines', 'bushes', 'frontTrees']
cents = np.array([np.median(ol[lm == LAYERS.index(n)], 0) for n in keep])
strip = out < 0
d2 = ((nl[strip][:, None, :] - cents[None]) ** 2).sum(-1)
cls = np.full(out.shape, -1, np.int16); cls[strip] = np.array([LAYERS.index(n) for n in keep])[d2.argmin(1)]
from skimage.filters.rank import majority
lut = np.unique(cls[strip]); idx = np.searchsorted(lut, np.where(strip, cls, lut[0]))
sm = lut[majority(idx.astype(np.uint16), np.ones((9, 9), bool))]
out[strip] = sm[strip]
# flowers in the strips
from v2_layermap import flower_mask
fm = flower_mask(new / 255.0) & strip & ~np.isin(out, [LAYERS.index('path'), LAYERS.index('pathEdges')])
out[fm] = LAYERS.index('flowers')
Image.fromarray(new).save(out_ref); np.save(out_lm, out)
print('strip px %d: %s' % (strip.sum(), {n: int(((out == LAYERS.index(n)) & strip).sum()) for n in LAYERS if ((out == LAYERS.index(n)) & strip).any()}))
