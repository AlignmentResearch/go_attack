#!/bin/bash -e
VICTIM_PATH="$1"
ADVERSARY_PATH="$2"

mkdir -p /shared/match/"$RUN_NAME"/
/engines/KataGo-custom/cpp/katago match \
    -config /go_attack/configs/match-base.cfg \
    -config /go_attack/configs/compute/1gpu.cfg \
    -override-config nnModelFile0="$VICTIM_PATH" \
    -override-config nnModelFile1="$ADVERSARY_PATH" \
    -sgf-output-dir /shared/match/"$RUN_NAME" \
    -log-file /shared/match/"$RUN_NAME"/match.log