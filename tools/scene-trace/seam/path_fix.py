"""Path consistency edits on B (after the seam edit): usage path_fix.py B_IN.png B_OUT.png [DEBUG_DIR]

1. tone   B's whole path (cream and its pebbles) shifted to A's path colour (median difference), feathered at the edges.
2. left   the left path edge from A's last row (x 385) continued smoothly down to the lamp island (y 115); the cream
          gap left of it is filled with A's own verge grass (A's last 116 rows translated down, aligned on the edge),
          colour-ramped towards the island grass; B's lamp arm, ring and foliage stay on top.
3. clean  soft shadow shapes cut by the join (B rows 0-150, path interior) replaced by the local clean cream.
4. pebble A's large tan pebbles continued into B's first ~450 rows, shrinking to B's own pebble size and thinning out,
          placed only in clean path interior away from edges and existing pebbles (delta-pasted, so they take B's cream).
A is never modified. Rows >= 500 change only by the tone shift (1)."""
import os
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
A = np.asarray(Image.open(os.path.join(HERE, '..', 'A.png')).convert('RGB')).astype(np.float64)
B = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(np.float64)
H, W = B.shape[:2]
rng = np.random.default_rng(5)


def cream(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    return (r > 215) & (g > 195) & (b > 160) & (r - b < 70) & (r >= g)


def path_mask(img):
    m = ndi.binary_opening(cream(img), iterations=2)
    lbl, n = ndi.label(m)
    sz = ndi.sum(m, lbl, range(1, n + 1))
    keep = np.isin(lbl, 1 + np.nonzero(sz > 20000)[0])
    return ndi.binary_fill_holes(ndi.binary_closing(keep, iterations=3))


out = B.copy()

# 1. tone ------------------------------------------------------------------------------------------------------------
pa, pb = path_mask(A), path_mask(B)
core = lambda img, m: img[ndi.binary_erosion(m & cream(img), iterations=4)]
delta = np.median(core(A, pa), 0) - np.median(core(B, pb), 0)
alpha = ndi.gaussian_filter(ndi.binary_dilation(pb, iterations=2).astype(float), 1.5)
out += alpha[..., None] * delta
print('tone delta', delta)

# 2. left edge -------------------------------------------------------------------------------------------------------
Y2 = 116


def left_edge(img, y):
    xs = np.flatnonzero(cream(img[y, 300:520]))
    return 300 + xs[0] if len(xs) else None


xa = left_edge(A, H - 1)                                  # A's path edge on its last row
xa_prev = left_edge(A, H - 30)
slope0 = (xa - xa_prev) / 29.0
xi = np.median([left_edge(B, y) for y in range(Y2, Y2 + 12)])  # lamp island edge below the gap
t = np.arange(Y2) / (Y2 - 1)
h00, h10, h01 = 2 * t**3 - 3 * t**2 + 1, t**3 - 2 * t**2 + t, -2 * t**3 + 3 * t**2
edge = h00 * xa + h10 * slope0 * (Y2 - 1) + h01 * xi        # Hermite: A's slope at the join, flat into the island
# A's own edge jitter (grass tufts): its last rows' edge minus a smooth trend, laid on the new edge
ae = np.array([left_edge(A, H - Y2 + y) or xa for y in range(Y2)], float)
edge = edge + np.clip(ae - ndi.gaussian_filter1d(ae, 6), -6, 6)
yy, xx = np.mgrid[0:Y2, 0:W]
inside = (xx < np.minimum(edge[:, None], 439)) & (xx > 300)
band = B[:Y2]
gl = (band[..., 1] > band[..., 0] + 6) & (band[..., 1] > band[..., 2] + 12)      # green foliage and grass: keep
wood = (band[..., 0] < 200) & (band[..., 0] > band[..., 2] + 25) & ~gl            # lamp arm and post: keep
metal = (np.abs(band[..., 0] - band[..., 2]) < 18) & (band.mean(-1) < 170)       # ring, hook: keep
fill = inside & ~ndi.binary_dilation(gl | wood | metal, iterations=1)
# source: one rigid patch of plain meadow grass from A (no flowers, no outlines), chosen closest to A's verge colour
ver_c = np.median(A[H - 60:H, 300:370].reshape(-1, 3), 0)
best, pos = 1e9, None
gA = np.hypot(ndi.sobel(A.mean(-1), 0), ndi.sobel(A.mean(-1), 1))
for py in range(200, H - 600, 12):
    for px in range(90, W - 260, 12):
        p = A[py:py + Y2, px:px + 170]
        if gA[py:py + Y2, px:px + 170].max() > 120:
            continue
        c = np.abs(np.median(p.reshape(-1, 3), 0) - ver_c).sum() + 0.3 * gA[py:py + Y2, px:px + 170].mean()
        if c < best:
            best, pos = c, (py, px)
py, px = pos
print('grass patch from A at', pos, 'cost', round(best, 1))
src = np.zeros((Y2, W, 3))
src[:, 270:440] = A[py:py + Y2, px:px + 170] - np.median(A[py:py + Y2, px:px + 170].reshape(-1, 3), 0) + ver_c
ib = B[Y2:Y2 + 70, 220:330].reshape(-1, 3)
ib = ib[(ib[:, 1] > ib[:, 0] + 6) & (ib[:, 1] > ib[:, 2] + 30) & (ib.mean(1) > 160)]   # island grass pixels only
isl = np.median(ib, 0)
print('verge', ver_c, 'island grass', isl)
ramp = np.clip((np.arange(Y2) - 40) / (Y2 - 40), 0, 1)[:, None, None]
src = src + ramp * (isl - ver_c)                                # verge colour eases into the island grass
# soft edge towards the path, like A's verge: alpha ramps over 4 px inside the edge curve
edist = edge[:, None] - xx
a2 = np.clip(edist / 4.0, 0, 1) * ndi.gaussian_filter(fill.astype(float), 1.0)
a2 = np.where(fill, a2, 0)
a2[:, :250] = 0
out[:Y2] = out[:Y2] * (1 - a2[..., None]) + src * a2[..., None]
left_mask = np.zeros((H, W)); left_mask[:Y2] = a2

# 3. clean shadows ---------------------------------------------------------------------------------------------------
Y3 = 150
pbo = path_mask(out)
interior = ndi.binary_erosion(pbo, iterations=6)
interior[Y3:] = False
G = out[..., 1]
_, (jy, jx) = ndi.distance_transform_edt(~interior, return_indices=True)
base = ndi.percentile_filter(G[jy, jx], 80, size=41)
deficit = (base - G) * interior
peb = ndi.binary_dilation(deficit > 9, iterations=3)          # hard pebbles keep
shadow = (deficit > 1.8) & ~peb & interior
shadow = ndi.binary_opening(shadow, iterations=1)
shadow = ndi.binary_dilation(shadow, iterations=2) & interior & ~peb
valid = interior & ~shadow
_, (iy, ix) = ndi.distance_transform_edt(~valid, return_indices=True)     # nearest clean cream for every pixel
filled = out[iy, ix]
clean_cream = np.stack([ndi.percentile_filter(filled[..., c], 80, size=41) for c in range(3)], -1)
grain = out - ndi.gaussian_filter(out, (2, 2, 0))
a3 = ndi.gaussian_filter(shadow.astype(float), 1.5)
a3[Y3:] = 0
out = out * (1 - a3[..., None]) + (clean_cream + 0.6 * grain) * a3[..., None]
print('shadow px cleaned', int(shadow.sum()))

# 4. pebbles ---------------------------------------------------------------------------------------------------------
la = A[..., 1]
ia = ndi.binary_erosion(pa, iterations=4)
basea = ndi.percentile_filter(np.where(ia, la, 0), 80, size=61)
pm = ((basea - la) > 8) & ia
lbl, n = ndi.label(pm)
sprites = []
for i, sl in enumerate(ndi.find_objects(lbl), 1):
    comp = lbl[sl] == i
    a = comp.sum()
    if not (250 < a < 2500) or sl[0].start < 1100:
        continue
    y0, y1, x0, x1 = sl[0].start - 3, sl[0].stop + 3, sl[1].start - 3, sl[1].stop + 3
    patch = A[y0:y1, x0:x1]
    m = ndi.binary_dilation(lbl[y0:y1, x0:x1] == i, iterations=2)
    if (lbl[y0:y1, x0:x1][m] != i).any() & ((lbl[y0:y1, x0:x1] > 0) & (lbl[y0:y1, x0:x1] != i)).any():
        continue
    bg = np.median(A[y0:y1, x0:x1][~m], 0)
    alpha_s = ndi.gaussian_filter(m.astype(float), 0.8)
    sprites.append((patch - bg, alpha_s, a))
sprites.sort(key=lambda s: -s[2])
print('pebble sprites', len(sprites))
pbo = path_mask(out)
dist = ndi.distance_transform_edt(pbo)
_, (ky, kx) = ndi.distance_transform_edt(~pbo, return_indices=True)
occupied = ndi.binary_dilation((ndi.percentile_filter(out[..., 1][ky, kx], 80, size=41) - out[..., 1]) * pbo > 8, iterations=14)
occupied |= ~pbo
peb_mask = np.zeros((H, W))
count = len(sprites) and 0
yb = 4
attempts = 0
placed = []
while yb < 450 and attempts < 4000:
    attempts += 1
    y = int(rng.uniform(4, 450))
    keep_p = (1 - y / 450) ** 1.5                            # thinning out towards B's own sparse pebbles
    if rng.random() > keep_p:
        continue
    xs = np.flatnonzero(pbo[y])
    if len(xs) == 0:
        continue
    x = int(rng.choice(xs))
    k = (1.0 - 0.5 * (y / 450)) * rng.uniform(0.75, 1.1)     # shrink to B's pebble size, with A's size variation
    d, a_s, _ = sprites[int(rng.integers(0, min(len(sprites), 5)))]
    hh, ww = max(3, int(d.shape[0] * k)), max(3, int(d.shape[1] * k))
    if dist[y, x] < max(hh, ww) / 2 + 10:
        continue
    y0, x0 = y - hh // 2, x - ww // 2
    if y0 < 2 or y0 + hh >= 500 or occupied[y0 - 6:y0 + hh + 6, x0 - 6:x0 + ww + 6].any():
        continue
    if any(abs(py - y) < 70 and abs(px - x) < 90 for py, px in placed):
        continue
    if len(placed) >= 7:
        break
    dd = np.stack([np.asarray(Image.fromarray(np.clip(d[..., c] + 128, 0, 255).astype(np.uint8)).resize((ww, hh), Image.LANCZOS)).astype(float) - 128 for c in range(3)], -1)
    aa = np.asarray(Image.fromarray((a_s * 255).astype(np.uint8)).resize((ww, hh), Image.LANCZOS)).astype(float) / 255
    out[y0:y0 + hh, x0:x0 + ww] += dd * aa[..., None]
    peb_mask[y0:y0 + hh, x0:x0 + ww] = np.maximum(peb_mask[y0:y0 + hh, x0:x0 + ww], aa)
    occupied[y0 - 6:y0 + hh + 6, x0 - 6:x0 + ww + 6] = True
    placed.append((y, x))
print('pebbles placed', len(placed), placed)

# 5. seam: remove the remaining low-frequency difference to A's last row, fading out over ~30 rows -------------------
d0 = ndi.gaussian_filter1d(A[H - 1] - out[0], 4, axis=0)
fade = np.exp(-np.arange(40) / 8.0)[:, None, None]
out[:40] += fade * d0[None]

Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8)).save(sys.argv[2])
if len(sys.argv) > 3:
    os.makedirs(sys.argv[3], exist_ok=True)
    np.savez(os.path.join(sys.argv[3], 'edits.npz'), left=left_mask.astype(np.float32),
             clean=np.pad(a3, ((0, 0), (0, 0)))[:H].astype(np.float32), pebbles=peb_mask.astype(np.float32))
