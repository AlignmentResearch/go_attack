#!/bin/sh
if [ $# -lt 1 ]; then
    echo "Must provide prefix for run" 1>&2
    exit 2
fi

RUN_NAME="$1-$(date +%Y.%m.%d-%H.%M.%S)"
echo "Run name: $RUN_NAME"

# shellcheck disable=SC2215
ctl job run --container \
    humancompatibleai/goattack:2022-09-19 \
    humancompatibleai/goattack:2022-09-19 \
    humancompatibleai/goattack:2022-09-19-python-v2 \
    humancompatibleai/goattack:2022-09-19-python-v2 \
    humancompatibleai/goattack:2022-09-19-python-v2 \
    --volume_name go-attack \
    --volume_mount shared \
    --command "/shared/kubernetes/victimplay.sh $RUN_NAME" \
    "/engines/KataGo-custom/cpp/evaluate_loop.sh /shared/victimplay/$RUN_NAME" \
    "/shared/kubernetes/train.sh $RUN_NAME" \
    "/shared/kubernetes/shuffle-and-export.sh $RUN_NAME" \
    "/shared/kubernetes/curriculum.sh $RUN_NAME" \
    --gpu 1 1 1 0 0 \
    --name go-training-"${RUN_NAME}" \
    --replicas "${2:-7}" 1 1 1 1
