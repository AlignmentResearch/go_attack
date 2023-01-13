#!/bin/bash

source "$(dirname "$(readlink -f "$0")")"/launch-common.sh

cd ~/go_attack || exit
docker build . -f compose/cpp/Dockerfile -t humancompatibleai/goattack:cpp
GIT_COMMIT=$(git rev-parse --short HEAD)
TWOGTP_IMG="humancompatibleai/goattack:twogtp-and-cpp-$GIT_COMMIT"
docker build . -f compose/transfer/twogtp-and-cpp/Dockerfile -t "$TWOGTP_IMG"
docker push "$TWOGTP_IMG"
echo "$TWOGTP_IMG"

NUM_GPUS=7
NUM_CPUS=224
PREFIX=ttseng-v10mil
RUN_NAME="$PREFIX-$(date +%Y%m%d-%H%M%S)"

~/sleipnir/ctl/ctl/ctl.py job run --container \
  "$TWOGTP_IMG" \
  $VOLUME_FLAGS \
  --command "bash -x
  /go_attack/kubernetes/gtp-eval.sh
  /shared/eval/$RUN_NAME" \
  --high-priority \
  --shared-host-dir-slow-tolerant \
  --gpu "$NUM_GPUS" \
  --cpu "$NUM_CPUS" \
  --name "go-gtp-$PREFIX" \
  --replicas 1
