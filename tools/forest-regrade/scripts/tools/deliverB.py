"""Phase B deliverables: heat maps, full frames, 3x crops, renderer-defect figure."""
import numpy as np
from PIL import Image, ImageDraw
from skimage.color import rgb2lab, deltaE_ciede2000
from score import rgb, to_device, lowpass, SP, DS, DOX, heat
D = SP + 'deliver/'
ref = rgb(SP + 'ref/ref.png')
def lab(img, s): return rgb2lab(lowpass(img, s))
# (a) low-passed dE00 heat at 1x (sigma 2), Phase A | Phase B, vmax 3
tiles = []
for tag, name in (('fitE', 'Phase A'), ('final', 'Phase B')):
    d = deltaE_ciede2000(lab(rgb(SP + f'out/{tag}/ref1x.png'), 2.0), lab(ref, 2.0))
    im = Image.fromarray((heat(d, 3) * 255).astype(np.uint8)).resize((468, 839), Image.BILINEAR)
    dr = ImageDraw.Draw(im); dr.text((6, 4), '%s  low-passed dE00 (0..3)  mean %.2f' % (name, d.mean()), fill=(255, 255, 255)); tiles.append(im)
sheet = Image.new('RGB', (468 * 2 + 8, 839), 'white'); sheet.paste(tiles[0], (0, 0)); sheet.paste(tiles[1], (476, 0)); sheet.save(D + 'phaseB_heat.png')
# (b) full frames at device 3x: Phase A | Phase B | reference (bicubic)
refd = Image.fromarray((to_device(ref) * 255 + .5).astype(np.uint8))
fr = [Image.open(SP + 'out/fitE/dev3x.png').convert('RGB'), Image.open(SP + 'out/final/dev3x.png').convert('RGB'), refd]
W, H = fr[0].size; full = Image.new('RGB', (3 * W + 24, H + 40), 'white'); dr = ImageDraw.Draw(full)
for i, (im, t) in enumerate(zip(fr, ['Phase A (approved)', 'Phase B', 'Reference, bicubic to device pixels'])):
    full.paste(im, (i * (W + 12), 40)); dr.text((i * (W + 12) + 8, 12), t, fill=(0, 0, 0))
full.save(D + 'phaseB_full.jpg', quality=92)
# (d) renderer defect: SwiftUI GPU path (old pb22 render) vs model vs CPU raster (final) at the same spot, 4x
x, y = 300, 1640
crops = [Image.open(SP + 'out/pb22/dev3x.png').convert('RGB'), Image.open(SP + 'out/pb22/model_dev3x.png').convert('RGB')]
labels = ['SwiftUI Canvas (GPU) - reversed AA', 'exact coverage model']
im3 = Image.new('RGB', (2 * 400 + 8, 420), 'white'); dr = ImageDraw.Draw(im3)
for i, (c, t) in enumerate(zip(crops, labels)):
    im3.paste(c.crop((x, y, x + 100, y + 100)).resize((400, 400), Image.NEAREST), (i * 408, 20)); dr.text((i * 408 + 4, 4), t, fill=(0, 0, 0))
im3.save(D + 'phaseB_renderer_defect.png')
print('ok')
