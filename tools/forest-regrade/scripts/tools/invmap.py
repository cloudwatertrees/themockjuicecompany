"""invmap.py IOS.png MODEL.png [OUT.png] : global iOS-vs-model check; lists clusters of large differences."""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
a = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(np.int16)
b = np.asarray(Image.open(sys.argv[2]).convert('RGB')).astype(np.int16)
d = np.abs(a - b).max(-1)
print('px>12 %d  px>40 %d  max %d' % ((d > 12).sum(), (d > 40).sum(), d.max()))
lab, n = ndi.label(ndi.binary_dilation(d > 40, iterations=6))
sl = ndi.find_objects(lab)
cl = sorted(((int((d[s] > 40).sum()), s) for s in sl), key=lambda t: -t[0])
for cnt, s in cl[:25]:
    print('  %4d px  x %d-%d  y %d-%d' % (cnt, s[1].start, s[1].stop, s[0].start, s[0].stop))
print('clusters', n)
if len(sys.argv) > 3:
    m = np.zeros(d.shape + (3,), np.uint8); m[..., :] = (a.mean(-1) * .35).astype(np.uint8)[..., None]
    m[d > 40] = (255, 40, 40)
    Image.fromarray(m).resize((d.shape[1] // 3, d.shape[0] // 3), Image.BOX).save(sys.argv[3])
