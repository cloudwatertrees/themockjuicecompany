#!/bin/zsh
# Full Phase B pipeline with final settings. usage: pb_run.sh SRC_DATA TAG
SP=/tmp/work
cd $SP/tools
B=$SP/out/B/$2
PY=$SP/venv/bin/python
$PY pb_regions.py $1 $B || exit 1
$PY pb_bounds.py $B || exit 1
$PY - <<PY || exit 1
import numpy as np, sys
sys.argv=['x']
from PIL import Image
from skimage.color import rgb2lab
from pb_merge_smooth import choose_cells
reg = np.load('$B' + '_reg.npy'); rl = rgb2lab(np.asarray(Image.open('$SP/ref/ref.png').convert('RGB')).astype(float)/255)
cell, rms = choose_cells(reg, rl)
area = np.bincount(reg.ravel(), minlength=len(cell)); cell[area > 5000] = 6
np.save('$B' + '_cell.npy', cell)
PY
PB_SIGCOST=2.0 PB_SIGIND=1.5 $PY pb_refine.py $B | grep -E "beads" || exit 1
PB_BLUR=0 PB_OPT=0.8 $PY pb_trace.py $B ${B}_shapes.json 2>&1 | grep -E "soft regions|traced" || exit 1
$PY pb_rims.py $B | grep -E "rim regions" || exit 1
PB_BLUR=0 PB_RIMS=1 PB_OPT=0.8 $PY pb_trace.py $B ${B}_shapes_r.json 2>&1 | grep -E "traced" || exit 1
PB_CONT_SOFT=1 $PY pb_fit.py $B ${B}_shapes_r.json $SP/data/$2 || exit 1
$PY pbrender.py $SP/data/$2 $SP/out/B/$2_1x.png
$PY -c "
from quick import score
import numpy as np; from PIL import Image
P = np.asarray(Image.open('$SP/out/B/$2_1x.png').convert('RGB')).astype(float)/255
print('$2 (model 1x): SSIM %.4f dE %.3f p95 %.2f | lp dE %.3f p95 %.2f max %.1f' % score(P))
"
# keep 4x maps for this tag
