#!/bin/zsh
# usage: render.sh dev|repo JOBFILE [DATADIR]
SP=/Users/laverath/Desktop/themockjuicecompany/tools/scene-trace/work
UDID=C79B1642-6DE6-4BD5-9BE2-8F6C49BC0929
if [[ $1 == dev ]]; then BID=com.scratch.forestrender; else BID=com.scratch.forestrender.repo; fi
SIMCTL_CHILD_RENDER_JOB=$2 SIMCTL_CHILD_ART_DATA_DIR=${3:-$SP/data/base} \
  xcrun simctl launch --console --terminate-running-process $UDID $BID 2>&1 | grep -v '^$' | grep -E 'wrote|timing|done|rror|atal' 
