#!/bin/sh
if [ $# -lt 1 ]; then
    echo "Must provide name for run" 1>&2
    exit 2
fi
python -m ctl.ctl job run --container \
    humancompatibleai/goattack:2022-08-23-v7 \
    humancompatibleai/goattack:2022-08-22-v2-python \
    humancompatibleai/goattack:2022-08-22-v2-python \
    --volume_name go-attack \
    --volume_mount shared \
    --command "/shared/kubernetes/victimplay.sh $1" \
    "/shared/kubernetes/train.sh $1" \
    "/shared/kubernetes/shuffle-and-export.sh $1" \
    --gpu 1 1 1 \
    --name go-training \
    --replicas ${2:-7} 1 1
