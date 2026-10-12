"""Zoomed device crops: render(s) vs reference bicubic-upscaled to same framing; nearest-neighbour zoom."""
import sys, numpy as np
from PIL import Image, ImageDraw
from score import rgb, to_device, SP, DS, DOX
REG = {'bridge': (250, 640, 370, 740), 'fox': (735, 960, 835, 1060), 'door': (720, 640, 820, 740),
       'flowers': (480, 1080, 580, 1180), 'treeedge': (650, 1180, 750, 1280), 'pebbles': (200, 1200, 300, 1300),
       'meadow': (100, 420, 200, 520), 'hedge': (640, 120, 740, 220)}
def crops(tags, names, z, out):
    refd = Image.fromarray((to_device(rgb(SP + 'ref/ref.png')) * 255 + 0.5).astype(np.uint8))
    srcs = [Image.open(SP + f'out/{t}/dev3x.png').convert('RGB') for t in tags] + [refd]
    labels = tags + ['reference (bicubic)']
    rows = []
    for k in names:
        x0, y0, x1, y1 = REG[k]
        b = (int(x0 * DS + DOX), int(y0 * DS), int(x1 * DS + DOX), int(y1 * DS)); w, h = b[2] - b[0], b[3] - b[1]
        r = Image.new('RGB', (len(srcs) * (w * z + 6), h * z + 14), (255, 255, 255))
        d = ImageDraw.Draw(r)
        for j, s in enumerate(srcs):
            r.paste(s.crop(b).resize((w * z, h * z), Image.NEAREST), (j * (w * z + 6), 14))
            d.text((j * (w * z + 6) + 3, 1), f'{k}: {labels[j]}', fill=(0, 0, 0))
        rows.append(r)
    W_ = max(r.width for r in rows); sheet = Image.new('RGB', (W_, sum(r.height + 6 for r in rows)), (255, 255, 255)); y = 0
    for r in rows: sheet.paste(r, (0, y)); y += r.height + 6
    sheet.save(out); print(out, sheet.size)
if __name__ == '__main__':
    crops(sys.argv[1].split(','), sys.argv[2].split(','), int(sys.argv[3]), sys.argv[4])
