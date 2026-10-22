import sys
from common import *
from fx.trees import bell_tree
from fx.paint import flat
from fx.geom import fmt, catmull_rom
box = (60, 1160, 300, 1440)
orig = render(in_box(load_live_layers(), box, 4), 2.5, box)
bg = flat('meadow', 'M0 0L937 0L937 1678L0 1678Z', 'E4DEA1')
sh = bell_tree(152, 1218, 66, tiers=3, seed=int(sys.argv[1]) if len(sys.argv) > 1 else 0)
new = render([bg] + sh, 2.5, box)
save(np.concatenate([orig, new], 1), SCRATCH / 'proto_tree.png')
print(len(sh), [s.nx for s in sh])
