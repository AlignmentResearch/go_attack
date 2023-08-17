#!/bin/bash -e
cd /engines/KataGo-custom/python
RUN_NAME="$1"
DIRECTORY="$2"
VOLUME_NAME="$3"
# 1 to enable gatekeeper, 0 to disable gatekeeper
USE_GATING="$4"

# not related to shuffle-and-export but we want some process to log this
/go_attack/kubernetes/log-git-commit.sh /"$VOLUME_NAME"/train-only/"$DIRECTORY"

mkdir -p /"$VOLUME_NAME"/train-only/"$DIRECTORY"
./selfplay/shuffle_and_export_loop.sh    "$RUN_NAME"    /"$VOLUME_NAME"/train-only/"$DIRECTORY"    /tmp    16    256    $USE_GATING
sleep infinity
