"""Device-framing crops (3x): render vs reference (bicubic to same framing), 1:1 device pixels."""
import sys, numpy as np
from PIL import Image
from score import rgb, to_device, SP, DS, DOX
tag = sys.argv[1]; out = sys.argv[2]
ren = Image.open(SP + f'out/{tag}/dev3x.png').convert('RGB')
refd = Image.fromarray((to_device(rgb(SP + 'ref/ref.png')) * 255 + 0.5).astype(np.uint8))
# design-space boxes -> device px
regions = {'bridge': (150, 600, 470, 860), 'fox': (690, 930, 880, 1110), 'door': (700, 600, 900, 860),
           'flowers': (380, 1040, 640, 1200), 'trees': (600, 1150, 860, 1450), 'meadow_hedge': (520, 120, 860, 420)}
sel = sys.argv[3].split(',') if len(sys.argv) > 3 else list(regions)
for k in sel:
    x0, y0, x1, y1 = regions[k]
    b = (int(x0 * DS + DOX), int(y0 * DS), int(x1 * DS + DOX), int(y1 * DS))
    w, h = b[2] - b[0], b[3] - b[1]
    c = Image.new('RGB', (2 * w + 8, h), (255, 255, 255))
    c.paste(ren.crop(b), (0, 0)); c.paste(refd.crop(b), (w + 8, 0))
    c.save(out + f'_{k}.png')
    print(k, c.size)
