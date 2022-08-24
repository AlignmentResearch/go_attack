#!/bin/sh
if [ $# -lt 1 ]; then
    echo "Must provide name for run" 1>&2
    exit 2
fi

VICTIM=${2:-/shared/victims/kata1-b20c256x2-s5303129600-d1228401921.bin.gz}

ctl job run --container \
    humancompatibleai/goattack:2022-08-23-v7 \
    humancompatibleai/goattack:2022-08-23-v7 \
    humancompatibleai/goattack:2022-08-22-v2-python \
    humancompatibleai/goattack:2022-08-22-v2-python \
    --volume_name go-attack \
    --volume_mount shared \
    --command "/shared/kubernetes/victimplay.sh $1 $VICTIM" \
    "python3 /shared/kubernetes/evaluate_loop.py $1 $VICTIM" \
    "/shared/kubernetes/train.sh $1" \
    "/shared/kubernetes/shuffle-and-export.sh $1" \
    --gpu 1 1 0 1 \
    --name go-training \
    --replicas "${3:-7}" 1 1 1
