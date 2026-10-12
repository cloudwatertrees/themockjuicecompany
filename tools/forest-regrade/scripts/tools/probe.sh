#!/bin/zsh
SP=/tmp/work
for K in "$@"; do
  $SP/venv/bin/python $SP/tools/probe.py $K ${KIND:-L}
  echo "full 393 852 3 $SP/exp/probe.png" > $SP/exp/jp.txt
  $SP/tools/render.sh dev $SP/exp/jp.txt $SP/exp/probe >/dev/null
  echo -n "K=$K "; $SP/venv/bin/python $SP/tools/invmap.py $SP/exp/probe.png $SP/exp/scenes/s1_model.png | head -1
done
