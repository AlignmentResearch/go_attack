#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd ${SCRIPT_DIR}

GIT_ROOT=$(git rev-parse --show-toplevel)
cd ${GIT_ROOT}

docker run \
    -v models:/models \
    -it $(docker build -f compose/cpp/Dockerfile -q .) \
    /engines/KataGo-raw/cpp/katago $@
