"""subset.py SRC_DATADIR OUT_DATADIR idx,idx,...  -> data dir holding only the given global shape indices."""
import sys
from pbart import load, write
shapes = load(sys.argv[1]); keep = {int(v) for v in sys.argv[3].split(',')}
write([s for k, s in enumerate(shapes) if k in keep], sys.argv[2])
