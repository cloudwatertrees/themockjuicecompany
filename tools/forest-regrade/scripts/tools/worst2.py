"""worst2.py TAG [T] [N] : tiles ranked by structural error (1-SSIM, luma) at 1x; sheet: render | reference (4x)."""
import sys, numpy as np
from PIL import Image
from skimage.metrics import structural_similarity
from score import rgb, luma, SP
tag = sys.argv[1]; T = int(sys.argv[2]) if len(sys.argv) > 2 else 32; n = int(sys.argv[3]) if len(sys.argv) > 3 else 12
ren = rgb(SP + f'out/{tag}/ref1x.png'); ref = rgb(SP + 'ref/ref.png')
_, smap = structural_similarity(luma(ren), luma(ref), data_range=1, gaussian_weights=True, sigma=1.5, use_sample_covariance=False, full=True)
err = 1 - smap; H, W = err.shape
sc = sorted(((err[y:y + T, x:x + T].mean(), y, x) for y in range(0, H - T + 1, T // 2) for x in range(0, W - T + 1, T // 2)), reverse=True)
picked = []
for s, y, x in sc:
    if all(abs(y - py) >= T or abs(x - px) >= T for _, py, px in picked): picked.append((s, y, x))
    if len(picked) == n: break
z = 4; R = Image.open(SP + f'out/{tag}/ref1x.png').convert('RGB'); F = Image.open(SP + 'ref/ref.png').convert('RGB')
cols = 2; tiles = []
for s, y, x in picked:
    print('tile x=%d y=%d  1-SSIM %.3f' % (x, y, s))
    t = Image.new('RGB', (2 * T * z + 4, T * z), 'white')
    t.paste(R.crop((x, y, x + T, y + T)).resize((T * z, T * z), Image.NEAREST), (0, 0)); t.paste(F.crop((x, y, x + T, y + T)).resize((T * z, T * z), Image.NEAREST), (T * z + 4, 0))
    tiles.append(t)
rows = (len(tiles) + cols - 1) // cols; tw, th = tiles[0].size
sheet = Image.new('RGB', (cols * (tw + 12), rows * (th + 12)), (255, 255, 255))
for i, t in enumerate(tiles): sheet.paste(t, ((i % cols) * (tw + 12), (i // cols) * (th + 12)))
sheet.save(sys.argv[4] if len(sys.argv) > 4 else SP + f'out/{tag}/worst2.png'); print(sheet.size)
