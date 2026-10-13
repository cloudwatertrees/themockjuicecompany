#!/bin/zsh
# usage: rs.sh TAG DATADIR  -> render ref-framing 1x + device 3x on iOS, score
SP=/tmp/work/fv2
mkdir -p $SP/out/$1
RS=($($SP/venv/bin/python -c "from PIL import Image; print(*Image.open('$SP/ref/ref.png').size)"))
printf "full $RS[1] $RS[2] 1 $SP/out/$1/ref1x.png\nfull 393 852 3 $SP/out/$1/dev3x.png\n" > $SP/out/$1/job.txt
$SP/tools/render.sh ${3:-dev} $SP/out/$1/job.txt $2 | grep -v wrote
cd $SP/tools && LABELS=$2 $SP/venv/bin/python score.py $1
