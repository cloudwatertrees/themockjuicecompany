#!/bin/zsh
# v2: the full refinement chain after v2_tail.sh: boundary fit on local colour fields -> trace + fit -> boundary fit on
# the fitted fills -> trace + fit -> fill refit with CELL px cells for large regions, mesh cap NMAX, soft boundaries crisp.
# usage: v2_chain.sh SRC TAG [lam] [CELL] [NMAX]   (SRC: an out/B tag with _reg/_layer/_pairs/_cell/_reg4; writes data/TAG)
SP=/Users/laverath/Desktop/themockjuicecompany/tools/scene-trace/work
cd $SP/tools
PY=$SP/venv/bin/python; B=$SP/out/B
LAM=${3:-16}; CELL=${4:-4}; NMAX=${5:-240}
$PY v2_edgefit.py $B/$1 $B/$2_a $LAM 8 | tail -1 || exit 1
zsh v2_retrace.sh $2_a $2_a 1.5 0.8 | tail -1 || exit 1
$PY v2_edgefit.py $B/$2_a $B/$2_b $LAM 8 $SP/data/$2_a $B/$2_a_shapes_r.json | tail -1 || exit 1
zsh v2_retrace.sh $2_b $2_b 1.5 0.8 | tail -1 || exit 1
PB_CONT_SOFT=0 zsh v2_refit.sh $2_b $2 $CELL $NMAX | grep -E "model 1x|M\b" || exit 1
