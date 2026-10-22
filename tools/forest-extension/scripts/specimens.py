"""Catalogue of live specimens (boxes + picks) and a contact sheet: python specimens.py [name ...]"""
import sys
import numpy as np
from common import *
from fx.specimen import Specimen

FOLIAGE = ('bushes', 'flowers', 'meadow', 'pines', 'frontTrees', 'backTrees', 'rocks', 'doorBush', 'hedge', 'pond', 'log')


def notpath(s):
    return s.layer not in ('path', 'pathEdges', 'bridge')


def notstone(s):
    """Exclude grey / lilac stone pieces (bridge stones, rock slivers) from plant specimens."""
    c = s.cols.mean(0)
    grey = c.max() - c.min() < 0.09
    lilac = c[2] > c[1] + 0.02 and abs(c[0] - c[1]) < 0.08
    return not (grey or lilac) or c.min() > 0.80


def foliage_only(s):
    """Exclude path rims/cream, lilac rock slivers and brown wood from tree groups."""
    c = s.cols.mean(0)
    cream = c[0] > 0.88 and c[1] > 0.82 and c[2] > 0.66 and c[0] - c[2] < 0.3
    lilac = c[2] > c[1] + 0.02 and abs(c[0] - c[1]) < 0.08
    brown = c[0] > c[1] + 0.12
    return not (cream or lilac or brown)


CATALOGUE = {
    # bushes / leaf clumps with flowers
    'bush_bridge': dict(box=(228, 880, 432, 1058), layers=('bushes', 'flowers', 'meadow'), merge='bushes', pick=notstone),
    'bush_pond': dict(box=(222, 268, 392, 425), layers=('bushes', 'flowers', 'meadow', 'pond'), pick=lambda s: s.layer != 'pond' or s.box[0] > 300),
    'bush_rightbridge': dict(box=(428, 755, 590, 870), layers=('bushes', 'flowers', 'meadow'), merge='bushes', pick=notstone),
    'bush_seamleft': dict(box=(0, 1555, 372, 1683), layers=('frontTrees', 'pines', 'rocks', 'bushes', 'flowers', 'meadow')),
    # ferns (hand-shaped leafy plants in the bushes layer)
    'fern_rockleft': dict(box=(522, 925, 615, 1030), layers=FOLIAGE, merge='bushes', margin=25,
                          pick=lambda s: not (abs(s.cols.mean(0)[0] - s.cols.mean(0)[1]) < 0.07 and s.cols.mean(0)[2] > s.cols.mean(0)[1])),
    'fern_rockright': dict(box=(700, 880, 775, 1000), layers=FOLIAGE, merge='bushes', margin=25,
                           pick=lambda s: not (abs(s.cols.mean(0)[0] - s.cols.mean(0)[1]) < 0.07 and s.cols.mean(0)[2] > s.cols.mean(0)[1])),
    'tuft_a': dict(box=(415, 1060, 495, 1112), layers=('meadow', 'bushes'), merge='bushes', margin=20),
    'tuft_b': dict(box=(200, 520, 290, 575), layers=('meadow', 'bushes'), merge='bushes', margin=20,
                   pick=lambda s: s.box[0] > 195),
    # rocks
    'rock_big': dict(box=(522, 848, 772, 1030), layers=FOLIAGE, max_size=260, merge='rocks'),
    'rock_seam': dict(box=(110, 1575, 290, 1683), layers=FOLIAGE, max_size=200, merge='rocks'),
    'rock_stack': dict(box=(720, 640, 910, 870), layers=('rocks',)),
    'stone_pond': dict(box=(268, 425, 345, 492), layers=('pond', 'rocks'), merge='rocks', margin=12),
    # trees
    'trees_br': dict(box=(615, 1035, 945, 1690), layers=FOLIAGE, max_size=420, merge='frontTrees',
                     pick=lambda s: s.layer not in ('pond', 'log') and (s.box[0] + s.box[2]) / 2 > 640 and foliage_only(s)),
    'trees_bl': dict(box=(-8, 1095, 175, 1690), layers=FOLIAGE, max_size=420, merge='frontTrees', margin=40, pick=foliage_only),
    'tree_bell': dict(box=(70, 1190, 245, 1440), layers=('frontTrees',), max_size=200, margin=30, merge='frontTrees'),
    'trees_ml': dict(box=(-8, 545, 125, 870), layers=FOLIAGE, max_size=360, merge='backTrees', pick=foliage_only),
    'trees_tl': dict(box=(-6, -6, 290, 340), layers=('backTrees',), max_size=360, merge='backTrees'),
    'trees_tr': dict(box=(640, -6, 940, 330), layers=('backTrees', 'frontTrees'), max_size=360, merge='backTrees'),
    'doorbush': dict(box=(640, 500, 945, 960), layers=('doorBush', 'hedge'), max_size=420, merge='frontTrees'),
    'hedge': dict(box=(540, -6, 945, 500), layers=('hedge',), max_size=480, merge='backTrees'),
    # pines
    'pine_top': dict(box=(320, 405, 510, 652), layers=FOLIAGE, max_size=260, merge='pines'),
    'pine_low': dict(box=(178, 1365, 372, 1640), layers=('pines', 'flowers', 'bushes'), max_size=260, merge='pines'),
    'lily': dict(box=(118, 380, 232, 474), layers=('pond',), merge='pond', margin=10,
                 pick=lambda s: not (s.cols.mean(0)[2] > 0.75 and s.cols.mean(0)[0] < 0.6 and max(s.box[2] - s.box[0], s.box[3] - s.box[1]) > 60)),
    'pad': dict(box=(205, 383, 280, 432), layers=('pond',), merge='pond', margin=8,
                pick=lambda s: not (s.cols.mean(0)[2] > 0.75 and s.cols.mean(0)[0] < 0.6 and max(s.box[2] - s.box[0], s.box[3] - s.box[1]) > 60)),
    'reeds': dict(box=(-6, 395, 118, 525), layers=('pond', 'bushes', 'flowers'), merge='pond', margin=20,
                  pick=lambda s: not (s.cols.mean(0)[2] > 0.70 and s.cols.mean(0)[0] < 0.6) and foliage_only(s) or s.cols.mean(0)[0] > s.cols.mean(0)[1] + 0.12),
    # pond and log
    'pond': dict(box=(-6, 300, 350, 520), layers=('pond',)),
    'log': dict(box=(680, 980, 910, 1140), layers=('log',)),
}


def get(name, **kw):
    d = dict(CATALOGUE[name]); d.setdefault('margin', 60); d.update(kw)
    merge = d.pop('merge', None)
    sp = Specimen(name, **d)
    sp.merge = merge
    return sp


if __name__ == '__main__':
    names = sys.argv[1:] or list(CATALOGUE)
    for n in names:
        sp = get(n)
        x0, y0, x1, y1 = sp.box
        sc = min(2.0, 700 / max(x1 - x0, y1 - y0))
        sh = [s for _, s, _ in sp.pieces]
        a = render(sh, sc, sp.box)
        b = render(ids_view([s for _, s, k in sp.pieces if k == 'object']) + [s for _, s, k in sp.pieces if k == 'ground'], sc, sp.box)
        save(np.concatenate([a, np.ones((a.shape[0], 4, 3)), b], 1), SCRATCH / f'spec_{n}.png')
        print(n, sp.counts(), 'ox %.0f base %.0f' % (sp.ox, sp.base_y))
