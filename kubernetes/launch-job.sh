#!/bin/sh
if [ $# -lt 1 ]; then
    echo "Must provide prefix for run" 1>&2
    exit 2
fi

GIT_ROOT=$(git rev-parse --show-toplevel)
RUN_NAME="$1-$(date +%Y%m%d-%H%M%S)"
echo "Run name: $RUN_NAME"

# Maybe build and push new Docker images
python "$GIT_ROOT"/kubernetes/update_images.py
# Load the env variables just created by update_images.py
# shellcheck disable=SC3046,SC1091
source "$GIT_ROOT"/kubernetes/active-images.env

# shellcheck disable=SC2215
ctl job run --container \
    "$CPP_IMAGE" \
    "$CPP_IMAGE" \
    "$PYTHON_IMAGE" \
    "$PYTHON_IMAGE" \
    "$PYTHON_IMAGE" \
    --volume_name go-attack \
    --volume_mount shared \
    --command "/shared/kubernetes/victimplay.sh $RUN_NAME" \
    "/engines/KataGo-custom/cpp/evaluate_loop.sh /shared/victimplay/$RUN_NAME" \
    "/shared/kubernetes/train.sh $RUN_NAME" \
    "/shared/kubernetes/shuffle-and-export.sh $RUN_NAME" \
    "/shared/kubernetes/curriculum.sh $RUN_NAME" \
    --gpu 1 1 1 0 0 \
    --name go-training-"$1" \
    --replicas "${2:-7}" 1 1 1 1
