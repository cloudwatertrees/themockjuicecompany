#!/bin/zsh
# v2: refit fills only (same geometry) with a different mesh cell for large regions and a different mesh cap.
# usage: v2_refit.sh SRC TAG CELL NMAX   (regions whose cell is 6, i.e. the large ones, get CELL)
SP=/tmp/work/fv2
cd $SP/tools
PY=$SP/venv/bin/python
for f in $SP/out/B/$1_*; do cp $f ${f/\/$1_/\/$2_}; done
$PY -c "
import numpy as np; c = np.load('$SP/out/B/$2_cell.npy'); c[c == 6] = $3; np.save('$SP/out/B/$2_cell.npy', c)"
PB_NMAX=$4 PB_CONT_SOFT=${PB_CONT_SOFT:-1} $PY pb_fit.py $SP/out/B/$2 $SP/out/B/$2_shapes_r.json $SP/data/$2 || exit 1
$PY pbrender.py $SP/data/$2 $SP/out/B/$2_1x.png
$PY -c "
from quick import score
import numpy as np; from PIL import Image
P = np.asarray(Image.open('$SP/out/B/$2_1x.png').convert('RGB')).astype(float)/255
print('$2 (model 1x, cell $3 nmax $4): SSIM %.4f dE %.3f p95 %.2f | lp dE %.3f p95 %.2f max %.1f' % score(P))
"
du -sh $SP/data/$2
