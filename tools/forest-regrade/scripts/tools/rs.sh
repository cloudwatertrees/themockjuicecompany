#!/bin/zsh
# usage: rs.sh TAG DATADIR  -> render ref-framing 1x + device 3x on iOS, score
SP=/tmp/work
mkdir -p $SP/out/$1
printf "full 937 1678 1 $SP/out/$1/ref1x.png\nfull 393 852 3 $SP/out/$1/dev3x.png\n" > $SP/out/$1/job.txt
$SP/tools/render.sh ${3:-dev} $SP/out/$1/job.txt $2 | grep -v wrote
cd $SP/tools && LABELS=$2 $SP/venv/bin/python score.py $1
