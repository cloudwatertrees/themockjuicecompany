"""v2: side-by-side 3x crops (reference bicubic-upscaled | render) at design-space boxes. usage: v2_crops.py TAG OUT.png"""
import sys, numpy as np
from PIL import Image
from score import rgb, to_device, SP, DS, DOX, DOY
tag, out = sys.argv[1], sys.argv[2]
ref = to_device(rgb(SP + 'ref/ref.png')); ren = rgb(SP + f'out/{tag}/dev3x.png')
boxes = [(130, 360, 250, 480), (160, 600, 300, 740), (730, 650, 870, 790), (690, 980, 830, 1120), (250, 960, 390, 1100), (20, 350, 140, 470)]
T = 330; tiles = []
for x0, y0, x1, y1 in boxes:
    X0, Y0, X1, Y1 = int(x0 * DS + DOX), int(y0 * DS + DOY), int(x1 * DS + DOX), int(y1 * DS + DOY)
    a = Image.fromarray((ref[Y0:Y1, X0:X1] * 255).astype(np.uint8)).resize((T, T), Image.LANCZOS)
    b = Image.fromarray((ren[Y0:Y1, X0:X1] * 255).astype(np.uint8)).resize((T, T), Image.LANCZOS)
    t = Image.new('RGB', (2 * T + 6, T), 'white'); t.paste(a, (0, 0)); t.paste(b, (T + 6, 0)); tiles.append(t)
o = Image.new('RGB', (2 * (2 * T + 6) + 12, 3 * (T + 8)), 'white')
for k, t in enumerate(tiles): o.paste(t, ((k % 2) * (2 * T + 18), (k // 2) * (T + 8)))
o.save(out)
