#!/bin/sh
if [ $# -lt 1 ]; then
    echo "Must provide name for run" 1>&2
    exit 2
fi

VICTIM=${2:-/shared/victims/kata1-b6c96-s41312768-d6061202.txt.gz}

ctl job run --container \
    humancompatibleai/goattack:2022-08-25-v2 \
    humancompatibleai/goattack:2022-08-25-v2 \
    humancompatibleai/goattack:2022-08-26-python-v3 \
    humancompatibleai/goattack:2022-08-26-python-v3 \
    --volume_name go-attack \
    --volume_mount shared \
    --command "/shared/kubernetes/victimplay.sh $1 $VICTIM" \
    "python3 /shared/kubernetes/evaluate_loop.py $1 $VICTIM" \
    "/shared/kubernetes/train.sh $1" \
    "/shared/kubernetes/shuffle-and-export.sh $1" \
    --gpu 1 1 1 0 \
    --name go-training \
    --replicas "${3:-7}" 1 1 1
