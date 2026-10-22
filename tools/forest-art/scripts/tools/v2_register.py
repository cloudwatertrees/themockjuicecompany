"""v2 step 2: register the current art's render to the new reference; report displacement and per-tile residuals.
usage: v2_register.py RENDER.png OUTDIR   (run from the working copy's tools/ so register.py/flow.py import)"""
import sys, numpy as np
from PIL import Image
from register import register, residual_tiles, ncc, pull
from flow import feat, rgb, SP

ren = rgb(sys.argv[1]); ref = rgb(SP + 'ref/ref.png'); out = sys.argv[2]
f = register(ren, ref)
np.save(out + '/field.npy', f)
mag = np.hypot(f[..., 0], f[..., 1])
print('field |d| median %.2f p75 %.2f p90 %.2f p99 %.2f max %.1f px' % tuple(np.percentile(mag, [50, 75, 90, 99, 100])))
print('edge NCC before %.4f after %.4f' % (ncc(feat(ren).astype(float), feat(ref).astype(float)), ncc(feat(ren).astype(float), pull(feat(ref), f))))
R = residual_tiles(ren, ref, f); m = np.hypot(R[:, 2], R[:, 3])
print('residual tiles %d: median %.2f p90 %.2f p99 %.2f' % (len(R), np.median(m), np.percentile(m, 90), np.percentile(m, 99)))
for y in range(60, 1678, 160):
    print(' '.join('%+3.0f,%+3.0f' % (f[y, x, 0], f[y, x, 1]) for x in range(50, 937, 105)))
vis = np.clip(mag / 20, 0, 1)
Image.fromarray((vis * 255).astype(np.uint8)).resize((469, 839)).save(out + '/fieldmag.png')
