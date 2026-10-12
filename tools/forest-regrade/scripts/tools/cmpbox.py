"""cmpbox.py TAG1,TAG2 x0,y0,x1,y1 Z OUT : device-pixel boxes side by side with reference (nearest zoom Z)."""
import sys, numpy as np
from PIL import Image
from score import rgb, to_device, SP
tags = sys.argv[1].split(','); x0, y0, x1, y1 = (int(v) for v in sys.argv[2].split(',')); z = int(sys.argv[3])
ims = [Image.open(SP + f'out/{t}/dev3x.png').convert('RGB') for t in tags] + [Image.fromarray((to_device(rgb(SP + 'ref/ref.png')) * 255 + .5).astype(np.uint8))]
w, h = x1 - x0, y1 - y0
c = Image.new('RGB', (len(ims) * (w * z + 6), h * z), 'white')
for i, im in enumerate(ims): c.paste(im.crop((x0, y0, x1, y1)).resize((w * z, h * z), Image.NEAREST), (i * (w * z + 6), 0))
c.save(sys.argv[4]); print(c.size)
