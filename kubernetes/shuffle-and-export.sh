#!/bin/bash -e
cd /engines/KataGo-custom/python
RUN_NAME="$1"
DIRECTORY="$2"
VOLUME_NAME="$3"
# 1 to enable gatekeeper, 0 to disable gatekeeper
USE_GATING="$4"

# not related to shuffle-and-export but we want some process to log this
/go_attack/kubernetes/log-git-commit.sh /"$VOLUME_NAME"/victimplay/"$DIRECTORY"

mkdir -p /"$VOLUME_NAME"/victimplay/"$DIRECTORY"
./selfplay/shuffle_and_export_loop.sh    "$RUN_NAME"    /"$VOLUME_NAME"/victimplay/"$DIRECTORY"    /tmp    16    256    $USE_GATING    -add-to-window 2790229817
sleep infinity
