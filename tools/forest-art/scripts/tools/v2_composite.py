"""v2: build a phone-shaped reference that keeps the original pixels. The generated tall image is resized so its copy of
the scene matches the original's scale (found by template matching over scale), aligned, and only its strips above and
below the original's footprint are used; the original goes in the middle unchanged and the seams are feathered.
Output width is the original's (937). Writes OUT.png and a seam preview.
V2_WARP=1 first warps the generated image onto the original with optical flow (needed when the generator redrew the scene).
usage: v2_composite.py GENERATED.png OLD_REF.png OUT.png [FEATHER_PX] [TARGET_H]"""
import sys, numpy as np, cv2
from PIL import Image

gen_p, old_p, out_p = sys.argv[1:4]
feather = int(sys.argv[4]) if len(sys.argv) > 4 else 24
target_h = int(sys.argv[5]) if len(sys.argv) > 5 else 2037
old = np.asarray(Image.open(old_p).convert('RGB')); H0, W0 = old.shape[:2]
gen = np.asarray(Image.open(gen_p).convert('RGB'))
gg, og = cv2.cvtColor(gen, cv2.COLOR_RGB2GRAY), cv2.cvtColor(old, cv2.COLOR_RGB2GRAY)

def match(s):
    o = cv2.resize(og, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    if o.shape[0] > gg.shape[0] or o.shape[1] > gg.shape[1]: return None
    _, m, _, loc = cv2.minMaxLoc(cv2.matchTemplate(gg, o, cv2.TM_CCOEFF_NORMED)); return m, loc
best = max(((match(s) or (-1, None))[0], s) for s in np.arange(0.70, 1.0, 0.005))
s0 = best[1]
best = max(((match(s) or (-1, None))[0], s) for s in np.arange(s0 - 0.01, s0 + 0.0101, 0.001))
sc = best[1]; m, (gx, gy) = match(sc)
print('scene in generated image: scale %.3f, offset (%d, %d), match %.3f' % (sc, gx, gy, m))
# resize generated so the scene is at the original's scale
k = 1 / sc
G = cv2.resize(gen, None, fx=k, fy=k, interpolation=cv2.INTER_LANCZOS4)
ox, oy = round(gx * k), round(gy * k)                    # where the original's top-left falls in G
print('generated resized to %dx%d; original footprint at (%d, %d)' % (G.shape[1], G.shape[0], ox, oy))
top_h, bot_h = oy, G.shape[0] - (oy + H0)
print('new art available: %d px above, %d px below (need %d total)' % (top_h, bot_h, target_h - H0))
# crop width: take columns so the original's columns line up, then fit to W0 (crop sides of strips)
x0 = ox; x1 = ox + W0
pad_l, pad_r = max(0, -x0), max(0, x1 - G.shape[1])
if pad_l or pad_r:
    print('generated is narrower than the original by %d/%d px: edge-padding strips' % (pad_l, pad_r))
    G = cv2.copyMakeBorder(G, 0, 0, pad_l, pad_r, cv2.BORDER_REPLICATE); x0 += pad_l; x1 += pad_l
G = G[:, x0:x1]
if __import__('os').environ.get('V2_WARP', '0') == '1':
    # the generated scene is a redraw: warp G toward the original with DIS flow measured inside the original's footprint,
    # extended into the strips by repeating the edge rows and fading the flow out over FADE px
    FADE = 160
    a = cv2.cvtColor(old, cv2.COLOR_RGB2GRAY); b = cv2.cvtColor(G[oy:oy + H0], cv2.COLOR_RGB2GRAY)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    fl = dis.calc(a, b, None)                                   # old(x) ~ G(x + fl)
    fl = cv2.GaussianBlur(fl, (0, 0), 12)
    print('flow in footprint: median |f| %.1f px, p90 %.1f px' % tuple(np.percentile(np.hypot(fl[..., 0], fl[..., 1]), [50, 90])))
    Hg = G.shape[0]
    full = np.zeros((Hg, W0, 2), np.float32)
    full[oy:oy + H0] = fl
    for y in range(oy):
        full[y] = fl[0] * max(0.0, 1 - (oy - y) / FADE)
    for y in range(oy + H0, Hg):
        full[y] = fl[-1] * max(0.0, 1 - (y - oy - H0) / FADE)
    gx, gy = np.meshgrid(np.arange(W0, dtype=np.float32), np.arange(Hg, dtype=np.float32))
    G = cv2.remap(G, gx + full[..., 0], gy + full[..., 1], cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
need_top = (target_h - H0) // 2; need_bot = target_h - H0 - need_top
need_top, need_bot = min(need_top, top_h), min(need_bot, bot_h)
out = np.concatenate([G[oy - need_top:oy], old, G[oy + H0:oy + H0 + need_bot]], 0).astype(np.float64)
print('canvas %dx%d (top strip %d, bottom strip %d)' % (out.shape[1], out.shape[0], need_top, need_bot))
# minimum-error seams: inside a band of BAND px at each end of the original, find per column the row where original and
# warped generated image differ least (dynamic programming, |dy| <= 1 per column), take generated above/below it
BAND = int(__import__('os').environ.get('V2_BAND', '140'))
Gc = G.astype(np.float64)
def seam(D):                      # D: band x W cost; returns row index per column
    h, w = D.shape; C = D.copy(); P = np.zeros((h, w), np.int8)
    for x in range(1, w):
        prev = C[:, x - 1]
        up = np.r_[np.inf, prev[:-1]]; dn = np.r_[prev[1:], np.inf]
        stack = np.stack([up, prev, dn]); k = stack.argmin(0)
        C[:, x] += stack.min(0); P[:, x] = k - 1
    y = int(C[:, -1].argmin()); rows = np.zeros(w, int)
    for x in range(w - 1, -1, -1):
        rows[x] = y; y += int(P[y, x])
    return rows
def soft(a, b): return cv2.GaussianBlur(np.abs(a - b).sum(-1), (0, 0), 2.0)
# top: band = original rows [0, BAND)
Dt = soft(old[:BAND].astype(np.float64), Gc[oy:oy + BAND]); Dt[:12] += 1e6                 # keep seam off the very first rows
rt = seam(Dt)
# bottom: band = original rows [H0-BAND, H0)
Db = soft(old[H0 - BAND:].astype(np.float64), Gc[oy + H0 - BAND:oy + H0]); Db[-12:] += 1e6
rb = seam(Db)
out = np.concatenate([G[oy - need_top:oy], old, G[oy + H0:oy + H0 + need_bot]], 0).astype(np.float64)
for x in range(W0):
    yt = need_top + rt[x]                         # rows above the seam come from the generated image
    out[:yt, x] = Gc[oy - need_top:oy + rt[x], x]
    yb = need_top + H0 - BAND + rb[x]             # rows below the seam come from the generated image
    out[yb:, x] = Gc[oy + H0 - BAND + rb[x]:oy + H0 + need_bot, x]
# 2 px feather along the seam lines
seam_mask = np.zeros(out.shape[:2], np.float32)
for x in range(W0):
    seam_mask[need_top + rt[x], x] = 1; seam_mask[need_top + H0 - BAND + rb[x], x] = 1
seam_mask = cv2.GaussianBlur(seam_mask, (0, 0), 1.5); seam_mask = np.clip(seam_mask / max(seam_mask.max(), 1e-6) * 1.0, 0, 1)
ref_full = np.concatenate([Gc[oy - need_top:oy], old, Gc[oy + H0:oy + H0 + need_bot]], 0)
out = out * (1 - 0.5 * seam_mask[..., None]) + 0.5 * seam_mask[..., None] * (0.5 * out + 0.5 * ref_full)
print('seam rows: top %d..%d, bottom %d..%d (inside the original, 0 = its first row)' % (rt.min(), rt.max(), rb.min(), rb.max()))
sy = [int(need_top + rt.mean()), int(need_top + H0 - BAND + rb.mean())]
out = np.clip(out, 0, 255).astype(np.uint8)
Image.fromarray(out).save(out_p)
prev = np.concatenate([out[max(0, y - 150):y + 150] for y in sy], 1)
Image.fromarray(prev).save(out_p.replace('.png', '_seams.png'))
# seam metric: mean abs colour step across each seam row vs typical row-to-row step
for y in sy:
    step = np.abs(out[y].astype(int) - out[y - 1].astype(int)).mean(); typ = np.abs(np.diff(out[y - 40:y + 40].astype(int), axis=0)).mean()
    print('seam at y=%d: step %.2f vs typical %.2f' % (y, step, typ))
