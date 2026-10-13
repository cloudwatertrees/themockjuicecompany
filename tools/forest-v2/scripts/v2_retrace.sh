#!/bin/zsh
# v2: rerun trace -> rims -> retrace -> fit from an existing 4x label map with other trace settings.
# V2_RIMS=0 skips pb_rims (no thin pale outline bands).
# usage: v2_retrace.sh SRC TAG SDF OPT   (SRC's _reg/_layer/_pairs/_cell/_reg4 are copied to TAG unless SRC = TAG)
SP=/tmp/work/fv2
cd $SP/tools
S=$SP/out/B/$1; B=$SP/out/B/$2
PY=$SP/venv/bin/python
[[ $1 != $2 ]] && for f in reg layer pairs cell reg4; do cp ${S}_$f.npy ${B}_$f.npy; done
PB_BLUR=0 PB_OPT=$4 $PY pb_trace.py $B ${B}_shapes.json 2>&1 | grep -E "traced|Error" || exit 1
if [[ ${V2_RIMS:-1} == 1 ]]; then
$PY pb_rims.py $B | grep -E "rim regions" || exit 1
PB_BLUR=0 PB_RIMS=1 PB_OPT=$4 PB_SDF=$3 $PY pb_trace.py $B ${B}_shapes_r.json 2>&1 | grep -E "traced|Error" || exit 1
else   # V2_RIMS=0: no separate thin pale outline bands (the reference's halos); SDF-smoothed trace of the label map
PB_BLUR=0 PB_OPT=$4 PB_SDF=$3 $PY pb_trace.py $B ${B}_shapes_r.json 2>&1 | grep -E "traced|Error" || exit 1
fi
PB_CONT_SOFT=1 $PY pb_fit.py $B ${B}_shapes_r.json $SP/data/$2 || exit 1
$PY pbrender.py $SP/data/$2 $SP/out/B/$2_1x.png
$PY -c "
from quick import score
import numpy as np; from PIL import Image
P = np.asarray(Image.open('$SP/out/B/$2_1x.png').convert('RGB')).astype(float)/255
print('$2 (model 1x, SDF $3 OPT $4): SSIM %.4f dE %.3f p95 %.2f | lp dE %.3f p95 %.2f max %.1f' % score(P))
"
