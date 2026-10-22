"""v2: floor of acuity.py's edge sigma: a perfectly hard edge at random angle and sub-pixel offset, exact area
anti-aliasing (as the CPU renderer does), measured with acuity.measure exactly as a 3x device render is.
usage: v2_acuity_floor.py [n]   (run from the working copy's tools/)"""
import sys, numpy as np
from acuity import measure

n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
rng = np.random.default_rng(0); S = 16; N = 41; out = []
for _ in range(n):
    th = rng.uniform(0, 2 * np.pi); c = N / 2 + rng.uniform(-0.5, 0.5, 2); nx, ny = np.cos(th), np.sin(th)
    yy, xx = (np.mgrid[0:N * S, 0:N * S] + 0.5) / S
    img = (((xx - c[0]) * nx + (yy - c[1]) * ny) > 0).reshape(N, S, N, S).mean((1, 3))
    out.append(measure(np.repeat(img[..., None], 3, 2), [(c[0], c[1], nx, ny)], 1.0, 0, 0)[0])
print('hard-edge floor @ device px: median %.3f  p25 %.3f  p75 %.3f' % tuple(np.nanpercentile(out, [50, 25, 75])))
