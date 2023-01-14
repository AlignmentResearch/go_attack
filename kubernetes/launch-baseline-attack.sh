#!/bin/bash

source "$(dirname "$(readlink -f "$0")")"/launch-common.sh
update_images cpp

NUM_GPUS=4
PREFIX=ttseng
RUN_NAME="$PREFIX-$(date +%Y%m%d-%H%M%S)"

# shellcheck disable=SC2086
ctl job run --container \
  "$CPP_IMAGE" \
  $VOLUME_FLAGS \
  --command "bash -x
  /go_attack/kubernetes/baseline-attack.sh
  /shared/baseline-attack/$RUN_NAME" \
  --high-priority \
  --gpu "$NUM_GPUS" \
  --name "go-baseline-$PREFIX" \
  --replicas 1
