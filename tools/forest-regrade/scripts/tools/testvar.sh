#!/bin/zsh
# usage: testvar.sh NAME [SWIFT_SRC]  -> builds dev host from SWIFT_SRC (default WIP), renders every scene, counts px>40 vs model
SP=/tmp/work
E=$SP/exp/scenes
ART_SRC=${2:-$SP/ForestPathIllustration.phaseB_wip.swift} $SP/tools/build_host.sh dev >/dev/null || { echo BUILD FAILED; exit 1; }
for s in s0 s1 r0 r1 r2 r3 p21; do
  echo "full 393 852 3 $E/${s}_$1.png" > $E/j.txt
  $SP/tools/render.sh dev $E/j.txt $E/$s >/dev/null
  echo -n "$1 $s: "; $SP/venv/bin/python $SP/tools/invmap.py $E/${s}_$1.png $E/${s}_model.png | head -1
  rm -f $E/${s}_$1.png
done
echo "timing 393 852 3 20" > $E/j.txt; $SP/tools/render.sh dev $E/j.txt $E/s0 | grep timing
