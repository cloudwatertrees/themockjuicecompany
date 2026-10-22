"""v2: which edges measure soft in a 3x device render, and why. Per acuity.py edge sample: render sigma, the reference's
own sigma at 1x, and how many distinct 4x labels the profile crosses within +-1.5 px (more than 2 = a ramp of thin bands).
usage: v2_acuity_why.py TAG BASE   (TAG: out/TAG/dev3x.png; BASE: out/B/X base with _reg4.npy; uses out/acuity_edges.npy)"""
import sys, numpy as np
from scipy import ndimage as ndi
from acuity import measure
from score import rgb, to_device, SP, DS, DOX, DOY

tag, base = sys.argv[1], sys.argv[2]
E = np.load(SP + 'out/acuity_edges.npy')
ref = rgb(SP + 'ref/ref.png')
s1 = measure(ref, E, 1.0, 0, 0, half=4.0, n=33)
s3 = measure(rgb(SP + f'out/{tag}/dev3x.png'), E, DS, DOX, DOY)
lab4 = np.load(base + '_reg4.npy'); U = 4
nl = []
for x, y, nx, ny in E:
    t = np.linspace(-1.5, 1.5, 25)
    X = np.clip(((x + t * nx) * U).astype(int), 0, lab4.shape[1] - 1); Y = np.clip(((y + t * ny) * U).astype(int), 0, lab4.shape[0] - 1)
    l = lab4[Y, X]; nl.append(1 + (l[1:] != l[:-1]).sum())
nl = np.array(nl); ok = ~np.isnan(s3) & ~np.isnan(s1)
print('edges %d; render sigma median %.3f' % (ok.sum(), np.median(s3[ok])))
for name, m in (('ref sharp (1x sigma < 0.6)', s1 < 0.6), ('ref medium (0.6-0.9)', (s1 >= 0.6) & (s1 < 0.9)), ('ref soft (>= 0.9)', s1 >= 0.9)):
    m = m & ok
    print('%-28s %4.0f%% of edges, render sigma median %.3f' % (name, 100 * m.sum() / ok.sum(), np.median(s3[m])))
for k in (1, 2, 3, 4):
    m = ok & ((nl == k) if k < 4 else (nl >= 4))
    if m.any(): print('label changes across +-1.5 px: %s  %4.0f%% of edges, render sigma median %.3f' % (str(k - 1) + ('+' if k == 4 else ''), 100 * m.sum() / ok.sum(), np.median(s3[m])))
# within reference-sharp edges: is extra softness from intermediate bands?
sh = ok & (s1 < 0.6)
for k in (2, 3, 4):
    m = sh & ((nl == k) if k < 4 else (nl >= 4))
    if m.any(): print('ref sharp, %d label changes: %4.0f%% of edges, render sigma median %.3f, p75 %.3f' % (k - 1, 100 * m.sum() / ok.sum(), np.median(s3[m]), np.percentile(s3[m], 75)))
np.save(SP + 'out/acuity_why_%s.npy' % tag, np.stack([s1, s3, nl], 1))
