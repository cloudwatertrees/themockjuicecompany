import sys, numpy as np
from PIL import Image
SP='/tmp/work/'
reg = np.load(sys.argv[1]); out = sys.argv[2]
ref = np.asarray(Image.open(SP+'ref/ref.png').convert('RGB')).astype(float)/255
e = np.zeros(reg.shape, bool); e[:, 1:] |= reg[:, 1:] != reg[:, :-1]; e[1:] |= reg[1:] != reg[:-1]
vis = ref.copy(); vis[e] = [1, 0, 0]
im = Image.fromarray((vis*255).astype(np.uint8))
boxes = [(150, 560, 550, 900), (560, 1100, 937, 1450), (0, 300, 400, 640), (560, 0, 937, 330)]
tiles = [im.crop(b).resize(((b[2]-b[0])*3//2, (b[3]-b[1])*3//2), Image.NEAREST) for b in boxes]
Wd = max(t.width for t in tiles[:2]) + max(t.width for t in tiles[2:]) + 8
sheet = Image.new('RGB', (tiles[0].width + tiles[2].width + 8, tiles[0].height + tiles[1].height + 8), (255,255,255))
sheet.paste(tiles[0], (0,0)); sheet.paste(tiles[1], (0, tiles[0].height+8)); sheet.paste(tiles[2], (tiles[0].width+8, 0)); sheet.paste(tiles[3], (tiles[0].width+8, tiles[2].height+8))
sheet.save(out)
