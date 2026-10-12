"""Geometry check: global + tiled sub-pixel shift between render and reference edge structure; edge-distance maps."""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2lab
from skimage.registration import phase_cross_correlation
from skimage.feature import canny
from score import rgb, SP, labelmap, GROUPS, LAYERS

def edge_strength(img):
    L = rgb2lab(img)
    g = sum(ndi.gaussian_gradient_magnitude(L[..., c], 1.0) ** 2 for c in range(3)) ** 0.5
    return g / (ndi.gaussian_filter(g, 12) + 2.0)

def edges(img, sig=1.2):
    L = rgb2lab(img)
    e = np.zeros(img.shape[:2], bool)
    for c, (lo, hi) in zip(range(3), [(2, 5), (2, 5), (2, 5)]):
        e |= canny(L[..., c], sigma=sig, low_threshold=lo, high_threshold=hi)
    return e

ren = rgb(SP + f'out/{sys.argv[1]}/{sys.argv[2]}'); ref = rgb(SP + 'ref/ref.png')
er, ef = edge_strength(ren), edge_strength(ref)
sh, err, _ = phase_cross_correlation(ef, er, upsample_factor=20, normalization=None)
print('global shift ref vs render (dy, dx) px: %.2f %.2f' % tuple(sh))
T = 96; shifts = []
for y in range(0, 1678 - T + 1, T // 2):
    for x in range(0, 937 - T + 1, T // 2):
        a, b = er[y:y + T, x:x + T], ef[y:y + T, x:x + T]
        if a.std() < 0.2 or b.std() < 0.2: continue
        s, e, _ = phase_cross_correlation(b, a, upsample_factor=10, normalization=None)
        shifts.append((y, x, s[0], s[1]))
S = np.array(shifts); mag = np.hypot(S[:, 2], S[:, 3])
print('tiles %d: |shift| median %.2f px, p90 %.2f, p99 %.2f, max %.2f; tiles >1px: %d' % (len(S), np.median(mag), np.percentile(mag, 90), np.percentile(mag, 99), mag.max(), (mag > 1).sum()))
for y, x, dy, dx in S[mag > 1]:
    print('   tile y=%4d x=%4d shift dy=%.1f dx=%.1f' % (y, x, dy, dx))
Er, Ef = edges(ren), edges(ref)
dr = ndi.distance_transform_edt(~Er); df = ndi.distance_transform_edt(~Ef)
print('reference edges within 1/2/3 px of a render edge: %.1f%% %.1f%% %.1f%%' % tuple(100 * (dr[Ef] <= k).mean() for k in (1, 2, 3)))
print('render edges within 1/2/3 px of a reference edge: %.1f%% %.1f%% %.1f%%' % tuple(100 * (df[Er] <= k).mean() for k in (1, 2, 3)))
lab = labelmap()
print('per region: ref-edge px >2px from render edge (%), render-edge px >2px from ref edge (%)')
for g, ls in GROUPS:
    m = np.isin(lab, [LAYERS.index(l) for l in ls])
    print('  %-8s %5.1f%%  %5.1f%%' % (g, 100 * (dr[Ef & m] > 2).mean(), 100 * (df[Er & m] > 2).mean()))
vis = np.ones(ref.shape) * 0.92
vis[Ef & (dr > 2)] = [0.85, 0.1, 0.1]   # in reference only
vis[Er & (df > 2)] = [0.1, 0.3, 0.9]    # in render only
vis[Ef & (dr <= 2)] = [0.55, 0.55, 0.55]
Image.fromarray((vis * 255).astype(np.uint8)).save(SP + f'out/{sys.argv[1]}/geom_edges.png')
