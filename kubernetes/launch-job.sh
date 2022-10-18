#!/bin/sh
GIT_ROOT=$(git rev-parse --show-toplevel)
RUN_NAME="ttseng-s34m-ov-vs-cp505-v16-$(date +%Y%m%d-%H%M%S)"
echo "Run name: $RUN_NAME"

# Make sure we don't miss any changes
if [ "$(git status --porcelain --untracked-files=no | wc -l)" -gt 0 ]; then
    echo "Git repo is dirty, aborting" 1>&2
    exit 1
fi

# Maybe build and push new Docker images
python "$GIT_ROOT"/kubernetes/update_images.py
# Load the env variables just created by update_images.py
# This line is weird because ShellCheck wants us to put double quotes around the
# $() context but this changes the behavior to something we don't want
# shellcheck disable=SC2046
export $(grep -v '^#' "$GIT_ROOT"/kubernetes/active-images.env | xargs)

ctl job run --container \
    ${CPP_IMAGE} \
    --volume_name go-attack --volume_mount shared \
    --command "/go_attack/kubernetes/match.sh /shared/match/${RUN_NAME}" \
    --gpu 4 \
    --name ttseng-match-sharpen-ov \
    --replicas 1 \
