#!/bin/zsh
# Phase B stages after the 1x region map (TAG_reg/_layer/_pairs exist). usage: pb_tail.sh TAG
SP=/Users/laverath/Desktop/themockjuicecompany/tools/scene-trace/work
cd $SP/tools
B=$SP/out/B/$1
PY=$SP/venv/bin/python
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
PB_BAND=2 PB_SIGCOST=2.0 PB_SIGIND=1.5 $PY pb_refine.py $B | grep -E "beads|protected" || exit 1
PB_BLUR=0 PB_OPT=0.8 $PY pb_trace.py $B ${B}_shapes.json 2>&1 | grep -E "traced|Error" || exit 1
$PY pb_rims.py $B | grep -E "rim regions" || exit 1
PB_BLUR=0 PB_RIMS=1 PB_OPT=0.8 PB_SDF=1.5 $PY pb_trace.py $B ${B}_shapes_r.json 2>&1 | grep -E "traced|Error" || exit 1
PB_CONT_SOFT=1 $PY pb_fit.py $B ${B}_shapes_r.json $SP/data/$1 || exit 1
$PY pbrender.py $SP/data/$1 $SP/out/B/$1_1x.png
$PY -c "
from quick import score
import numpy as np; from PIL import Image
P = np.asarray(Image.open('$SP/out/B/$1_1x.png').convert('RGB')).astype(float)/255
print('$1 (model 1x): SSIM %.4f dE %.3f p95 %.2f | lp dE %.3f p95 %.2f max %.1f' % score(P))
"
