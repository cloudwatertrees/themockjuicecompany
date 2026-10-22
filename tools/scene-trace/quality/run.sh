#!/bin/zsh
# usage: run.sh TAG IMAGE REGIONS  (env: EDGE_TAU CONTOUR_SMOOTHING TRACE_TOLERANCE)  -> quality/TAG/{art.swift,data/,log}
Q=${0:A:h}; mkdir -p $Q/$1
cd $Q/../i2s && ../work/venv/bin/python pipeline.py $2 --out $Q/$1/art.swift --regions $3 --work $Q/$1/w --workers ${WORKERS:-3} --no-soft > $Q/$1/log 2>&1
cd $Q/../work && venv/bin/python tools/extract.py $Q/$1/art.swift $Q/$1/data > /dev/null
