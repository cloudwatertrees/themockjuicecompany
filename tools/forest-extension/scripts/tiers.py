"""Segment live bell-tree tiers: base piece (large, bell/scallop silhouette, tree layer) + the later pieces whose centre
lies inside it. python tiers.py -> contact sheet of all tiers (index, bbox)."""
import numpy as np
from common import *
from fx.specimen import live
from fx.paint import _inside, area

TREE_LAYERS = ('frontTrees', 'backTrees')


def touches_edge(s, tol=1.5):
    b = s.box
    return b[0] + 1 < tol or b[2] - 1 > W - tol or b[1] + 1 < tol or b[3] - 1 > H - tol


def find_tiers(min_area=2200):
    L = live()
    order = {id(s): i for i, s in enumerate(L)}
    tiers = []
    for i, s in enumerate(L):
        if s.layer not in TREE_LAYERS or s.nx < 6:
            continue
        a = area(s.subs)
        if a < min_area:
            continue
        c = s.cols.mean(0)
        if not (c[1] > c[0] + 0.03):                    # green
            continue
        members = [s]
        for j in range(i + 1, min(i + 400, len(L))):
            t = L[j]
            if t.layer != s.layer:
                break
            tb = t.box
            cx, cy = (tb[0] + tb[2]) / 2, (tb[1] + tb[3]) / 2
            if area(t.subs) < a * 0.8 and tb[0] >= s.box[0] - 4 and tb[2] <= s.box[2] + 4 and tb[1] >= s.box[1] - 4 and tb[3] <= s.box[3] + 4 \
                    and _inside(s.subs, np.array([cx]), np.array([cy]))[0]:
                members.append(t)
        tiers.append(dict(index=len(tiers), order=i, base=s, members=members, area=a, edge=touches_edge(s),
                          box=[round(v, 1) for v in s.box]))
    return tiers


if __name__ == '__main__':
    T = find_tiers()
    ims = []
    from PIL import Image, ImageDraw
    for t in T:
        b = t['base'].box
        sc = 150 / max(b[2] - b[0], b[3] - b[1])
        im = render(t['members'], sc, b)
        pil = Image.fromarray((np.clip(im, 0, 1) * 255).astype(np.uint8)).resize((150, int(150 * (b[3] - b[1]) / (b[2] - b[0]))) if b[2] - b[0] >= b[3] - b[1] else (int(150 * (b[2] - b[0]) / (b[3] - b[1])), 150))
        canvas = Image.new('RGB', (156, 172), (255, 255, 255)); canvas.paste(pil, (3, 3))
        ImageDraw.Draw(canvas).text((3, 158), '%d %s n%d%s' % (t['index'], t['base'].layer[:5], len(t['members']), ' E' if t['edge'] else ''), fill=(0, 0, 0))
        ims.append(np.asarray(canvas))
    cols = 9
    rows = [np.concatenate(ims[r * cols:(r + 1) * cols] + [np.full_like(ims[0], 255)] * (cols - len(ims[r * cols:(r + 1) * cols])), 1) for r in range((len(ims) + cols - 1) // cols)]
    Image.fromarray(np.concatenate(rows, 0)).save(SCRATCH / 'tiers.png')
    print(len(T), 'tiers;', sum(not t['edge'] for t in T), 'not touching edges')
