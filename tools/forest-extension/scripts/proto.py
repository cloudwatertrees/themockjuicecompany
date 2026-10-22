"""Prototype views: original crop (all live layers) beside the recipe output on a flat meadow, same crop and scale.
usage: python proto.py NAME [seed]"""
import sys
from common import *
from fx.paint import flat

def P_tree(seed):
    from fx.trees import bell_tree
    return (60, 1160, 300, 1440), 2.5, bell_tree(152, 1218, 66, tiers=3, seed=seed)

def P_pine(seed):
    from fx.plants import fern_pine
    return (330, 410, 500, 640), 3.0, fern_pine(415, 432, 80, tiers=3, seed=seed)

def P_bush(seed):
    from fx.plants import leaf_clump, flower
    sh = leaf_clump(318, 990, 78, seed=seed)
    sh += flower(323, 963, 17, 'white', seed) + flower(360, 984, 13, 'white', seed + 1)
    sh += flower(408, 980, 12, 'lilac', seed + 2) + flower(383, 1013, 13, 'lilac', seed + 3)
    return (230, 880, 430, 1050), 3.5, sh

def P_rock(seed):
    from fx.stones import rock
    return (530, 850, 760, 1020), 3.0, rock(620, 995, 150, 135, seed) + rock(690, 1003, 40, 30, seed + 1) + rock(645, 1012, 45, 30, seed + 2)

name = sys.argv[1]; seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
box, sc, sh = globals()['P_' + name](seed)
orig = render(in_box(load_live_layers(), box, 4), sc, box)
bg = flat('meadow', 'M-10 -10L947 -10L947 1700L-10 1700Z', 'E4DEA1')
new = render([bg] + sh, sc, box)
save(np.concatenate([orig, new], 1), SCRATCH / f'proto_{name}.png')
print(name, len(sh), 'shapes')
