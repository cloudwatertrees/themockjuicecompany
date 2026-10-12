"""inv.py IOS_PNG DATADIR x0 y0 w h : model vs iOS on a device-framing crop; counts reversed-coverage edge pixels."""
import sys, numpy as np
from PIL import Image
from pbrender import render
from pbart import load
from score import DS, DOX
png, d = sys.argv[1], sys.argv[2]; x, y, w, h = (int(v) for v in sys.argv[3:7])
shapes = load(d)
dx0 = (x - DOX) / DS; dy0 = y / DS; dx1 = (x + w - DOX) / DS; dy1 = (y + h) / DS
sub = [s for s in shapes if s.box[0] <= dx1 and s.box[2] >= dx0 and s.box[1] <= dy1 and s.box[3] >= dy0]
m = render(sub, DS, DOX - x, -y, w, h)
m = (np.clip(m, 0, 1) * 255 + .5).astype(int)
i = np.asarray(Image.open(png).convert('RGB').crop((x, y, x + w, y + h))).astype(int)
bg = np.asarray(Image.open(png).convert('RGB')).astype(int)[0, 0]
d = np.abs(i - m).max(-1)
print('shapes %d  max %d  px>12 %d  px>40 %d' % (len(sub), d.max(), (d > 12).sum(), (d > 40).sum()))
