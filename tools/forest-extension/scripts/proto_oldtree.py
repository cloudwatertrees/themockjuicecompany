import sys
from common import *
from fx.specimen import live, live_ground_at
from fx.oldtree import old_tree
from fx.paint import flat
seed = int(sys.argv[1]) if len(sys.argv) > 1 else 0
box_live = (560, 1040, 937, 1500)
a = render(in_box(live(), box_live, 4), 1.6, box_live)
ground = lambda X, Y: live_ground_at(np.clip(X, 0, 936) * 0 + 300, np.clip(Y, 0, 1677) * 0 + 1050)
bg = flat('meadow', 'M0 0L937 0L937 3000L0 3000Z', 'E2DC9F')
sh = old_tree(760, 1440, ground, 1.0, seed)
b = render([bg] + sh, 1.6, box_live)
save(np.concatenate([a, np.ones((a.shape[0], 4, 3)), b], 1), SCRATCH / 'proto_oldtree.png')
print(len(sh))
