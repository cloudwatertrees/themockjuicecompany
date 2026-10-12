#!/bin/zsh
# usage: relocate.sh WORKDIR
# The scripts in tools/ were written with one hard-coded working directory (the old session scratch folder). This
# builds a working copy at WORKDIR (tools/ host/ ref/ data/ out/ venv/) with that path rewritten, ready to run.
# Needs: python3, Xcode + an iOS 18 simulator (UDID is hard-coded in build_host.sh/render.sh), potrace (brew install potrace).
set -e
HERE=${0:A:h}; W=${1:?workdir}
OLD=/tmp/work
mkdir -p $W/tools $W/host $W/ref $W/data $W/out
cp $HERE/tools/* $W/tools/; cp $HERE/host/Host.swift $W/host/; cp $HERE/inputs/ref/ref.png $W/ref/
for d in $HERE/inputs/data/*; do rm -rf $W/data/${d:t}; cp -R $d $W/data/${d:t}; done
sed -i '' "s#$OLD#$W#g" $W/tools/*
[[ -d $W/venv ]] || { python3 -m venv $W/venv; $W/venv/bin/pip install -q -r $HERE/requirements.txt; }
echo "ready: $W   (pip install -r requirements-phaseA.txt into $W/venv for register.py/flow.py)"
