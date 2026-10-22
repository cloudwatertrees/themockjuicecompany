"""Side-by-side crops at phone 3x: source (aspect-filled, Lanczos) | render.  usage: sbs.py SRC.png RENDER_PHONE.png OUT.png x0 y0 x1 y1
Box in design units (937x1678). The render is the 1179x2556 phone raster of the same screen."""
import sys
from PIL import Image
src, ren, out = sys.argv[1:4]
x0, y0, x1, y1 = map(float, sys.argv[4:8])
s = 2556 / 1678; ox = (1179 - 937 * s) / 2
S = Image.open(src).convert('RGB').resize((round(937 * s), 2556), Image.LANCZOS)
R = Image.open(ren).convert('RGB')
bx = (round(x0 * s + ox), round(y0 * s), round(x1 * s + ox), round(y1 * s))
a = S.crop((bx[0] - round(ox), bx[1], bx[2] - round(ox), bx[3])); b = R.crop(bx)
k = min(2.0, 700 / a.width)
a = a.resize((round(a.width * k), round(a.height * k)), Image.NEAREST); b = b.resize(a.size, Image.NEAREST)
c = Image.new('RGB', (a.width * 2 + 6, a.height), 'white'); c.paste(a, (0, 0)); c.paste(b, (a.width + 6, 0)); c.save(out)
