#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd ${SCRIPT_DIR}

GIT_ROOT=$(git rev-parse --show-toplevel)
cd ${GIT_ROOT}

# Get which submodule to use (raw or custom)
KATAGO_TYPE=$1; shift

# Get the Docker image to use
# Should be built already
DOCKER_IMAGE=$1; shift

# Get gpu index
GPU_INDEX=$1; shift

# Build and run the Docker image
# Manually change the assigned GPU devices as needed.
docker run \
    --gpus device=$GPU_INDEX \
    -v ${GIT_ROOT}/sabaki/models:/models \
    -it $DOCKER_IMAGE \
    /engines/KataGo-$KATAGO_TYPE/cpp/katago $@
