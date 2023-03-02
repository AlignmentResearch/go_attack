#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd ${SCRIPT_DIR}

GIT_ROOT=$(git rev-parse --show-toplevel)
cd ${GIT_ROOT}

# Get which submodule to use (raw or custom)
KATAGO_TYPE=$1; shift

# Build and run the Docker image
# Manually change the assigned GPU devices as needed.
docker run \
    --gpus device=5 \
    -v ${GIT_ROOT}/sabaki/models:/models \
    -it $(docker build -f compose/cpp/Dockerfile -q .) \
    /engines/KataGo-$KATAGO_TYPE/cpp/katago $@
