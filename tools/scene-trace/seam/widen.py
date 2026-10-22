"""Widen B's path towards A's width without deforming the scenery.

usage: widen.py B_IN.png B_OUT.png [K] [MAXSHIFT]
Per row, the content left of the path moves left and the content right of it moves right as rigid blocks (shapes are
kept; only the plain cream between the two edges stretches). The added width is (K - 1) x the local path width,
capped at 2 x MAXSHIFT, smoothed along y (sigma 80 rows) so the shift changes slowly (little shear), and ramped in from
0 at the join, where B's path already continues A's (279 px). Anchors sit 10 px inside the path edges so the edges,
their grass lips and banks move with their side. Prints the width profile before/after and the maximum shear."""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.ndimage import map_coordinates

src, dst = sys.argv[1], sys.argv[2]
K = float(sys.argv[3]) if len(sys.argv) > 3 else 1.25
MAXS = float(sys.argv[4]) if len(sys.argv) > 4 else 50
B = np.asarray(Image.open(src).convert('RGB')).astype(np.float64)
H, W = B.shape[:2]
r, g, b = B[..., 0], B[..., 1], B[..., 2]
cream = (r > 215) & (g > 195) & (b > 160) & (r - b < 70) & (r >= g)
m = ndi.binary_opening(cream, iterations=2)
lbl, n = ndi.label(m)
sz = ndi.sum(m, lbl, range(1, n + 1))
path = ndi.binary_fill_holes(ndi.binary_closing(lbl == 1 + np.argmax(sz), iterations=4))
L = np.full(H, np.nan); R = np.full(H, np.nan)
for y in range(H):
    xs = np.flatnonzero(path[y])
    if len(xs):
        L[y], R[y] = xs[0], xs[-1]
ok = ~np.isnan(L)
yy = np.arange(H)
L = np.interp(yy, yy[ok], L[ok]); R = np.interp(yy, yy[ok], R[ok])
Ls, Rs = ndi.gaussian_filter1d(L, 20), ndi.gaussian_filter1d(R, 20)
w = Rs - Ls
add = np.clip(w * (K - 1), 0, 2 * MAXS)
add = ndi.gaussian_filter1d(add, 80, mode='nearest')
ramp = np.clip(yy / 220.0, 0, 1)
ramp = ramp * ramp * (3 - 2 * ramp)
add *= ramp
# split of the added width between the sides: where an important object sits near the right screen edge (the mushroom
# island, B rows ~40-340) most of it goes to the left, so the object stays inside the phone-visible range
right_share = np.full(H, 0.5)
right_share[40:340] = 0.15
right_share = ndi.gaussian_filter1d(right_share, 40, mode='nearest')
half = add / 2
hl, hr = add * (1 - right_share), add * right_share
shear = max(np.abs(np.diff(hl)).max(), np.abs(np.diff(hr)).max())
print(f'path width before: mean {w.mean():.0f}, min {w.min():.0f}, max {w.max():.0f}; added: mean {add.mean():.0f}, max {add.max():.0f}; '
      f'max shift left {hl.max():.1f} px, right {hr.max():.1f} px; max shear {shear:.3f} px/row ({np.degrees(np.arctan(shear)):.1f} deg)')
out = np.empty_like(B)
xt = np.arange(W, dtype=np.float64)
for y in range(H):
    la, ra = Ls[y] + 10, Rs[y] - 10                       # anchors just inside the path edges
    tx = [-10, la - hl[y], ra + hr[y], W + 10]
    sx = [-10 + hl[y], la, ra, W + 10 - hr[y]]
    s = np.interp(xt, tx, sx)
    for c in range(3):
        out[y, :, c] = map_coordinates(B[y:y + 1, :, c], [np.zeros(W), s], order=3, mode='nearest')
Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8)).save(dst)
wn = (Rs + hr) - (Ls - hl)
print(f'path width after: mean {wn.mean():.0f}, min {wn.min():.0f}, max {wn.max():.0f}')
