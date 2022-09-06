#!/bin/sh
if [ $# -lt 1 ]; then
    echo "Must provide name for run" 1>&2
    exit 2
fi

# shellcheck disable=SC2215
ctl job run --container \
    humancompatibleai/goattack:2022-09-02-v2 \
    humancompatibleai/goattack:2022-09-02-v2 \
    humancompatibleai/goattack:2022-09-02-v2-python \
    humancompatibleai/goattack:2022-09-02-v2-python \
    humancompatibleai/goattack:2022-09-02-v2-python \
    --volume_name go-attack \
    --volume_mount shared \
    --command "/shared/kubernetes/victimplay.sh $1" \
    "/engines/KataGo-custom/cpp/evaluate_loop.sh /shared/victimplay/$1" \
    "/shared/kubernetes/train.sh $1" \
    "/shared/kubernetes/shuffle-and-export.sh $1" \
    "/shared/kubernetes/curriculum.sh $1" \
    --gpu 1 1 1 0 0 \
    --name go-training \
    --replicas "${2:-7}" 1 1 1 1
