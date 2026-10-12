#!/bin/zsh
# usage: pb_all.sh SRC_DATA TAG  -> out/B/TAG_* and data/TAG
SP=/tmp/work
cd $SP/tools
B=$SP/out/B/$2
$SP/venv/bin/python pb_regions.py $1 $B || exit 1
$SP/venv/bin/python pb_bounds.py $B || exit 1
$SP/venv/bin/python - <<PY || exit 1
import numpy as np, sys
sys.argv=['x']
from PIL import Image
from skimage.color import rgb2lab
from pb_merge_smooth import choose_cells
reg = np.load('$B' + '_reg.npy'); rl = rgb2lab(np.asarray(Image.open('$SP/ref/ref.png').convert('RGB')).astype(float)/255)
cell, rms = choose_cells(reg, rl); np.save('$B' + '_cell.npy', cell); print('cells', dict(zip(*np.unique(cell, return_counts=True))))
PY
$SP/venv/bin/python pb_refine.py $B || exit 1
PB_BLUR=${PB_BLUR:-0} $SP/venv/bin/python pb_trace.py $B ${B}_shapes.json 2>&1 | grep -v " / " || exit 1
PB_CONT_SOFT=1 $SP/venv/bin/python pb_fit.py $B ${B}_shapes.json $SP/data/$2 || exit 1
$SP/venv/bin/python pbrender.py $SP/data/$2 $SP/out/B/$2_1x.png
$SP/venv/bin/python -c "
from quick import score
import numpy as np; from PIL import Image
P = np.asarray(Image.open('$SP/out/B/$2_1x.png').convert('RGB')).astype(float)/255
print('$2 (python model, 1x): SSIM %.4f dE %.3f p95 %.2f | lp dE %.3f p95 %.2f max %.1f' % score(P))
"
