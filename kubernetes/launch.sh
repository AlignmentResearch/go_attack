#!/bin/bash -eu

source "$(dirname "$(readlink -f "$0")")"/launch-common.sh
update_images "cpp"

VICTIMPLAY_FLAGS="ttseng-cache-size-bench-20230830 shared"

ctl job run --container \
    "$CPP_IMAGE" \
    "$CPP_IMAGE" \
    "$CPP_IMAGE" \
    $VOLUME_FLAGS \
    --command \
    "/go_attack/kubernetes/victimplay21.sh $VICTIMPLAY_FLAGS" \
    "/go_attack/kubernetes/victimplay22.sh $VICTIMPLAY_FLAGS" \
    "/go_attack/kubernetes/victimplay23.sh $VICTIMPLAY_FLAGS" \
    --memory 72Gi 72Gi 72Gi \
    --gpu 1 1 1 \
    --name go-cache-size-bench \
    --replicas 3 3 3
