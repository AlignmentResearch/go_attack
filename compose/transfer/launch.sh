#!/bin/bash

function usage() {
  echo "Usage: $0 experiment command"
  echo
  echo "Launches a transfer experiment."
  echo
  echo "positional arguments:"
  echo "  experiment  Which experiment to run."
  echo "              values: {baseline-attack-vs-elf, baseline-attack-vs-leela}"
  echo "  command     docker-compose command to run."
  echo "              values: {build, up}"
}

if [ $# -ne 2 ]; then
  usage; exit 1
fi

EXPERIMENT_NAME=$1
DOCKER_COMPOSE_COMMAND=$2

# Exported variables like these are used inside the docker-compose yml file.
export HOST_REPO_ROOT=$(git rev-parse --show-toplevel)
export HOST_OUTPUT_DIR=${HOST_REPO_ROOT}/transfer-logs/${EXPERIMENT_NAME}
mkdir --parents ${HOST_OUTPUT_DIR}
if [ ${EXPERIMENT_NAME} = "baseline-attack-vs-leela" ]; then
  export HOST_LEELA_TUNING_FILE=${HOST_REPO_ROOT}/engines/leela/leelaz_opencl_tuning
  touch -a ${HOST_LEELA_TUNING_FILE}
fi

# Directory of this script
SCRIPT_DIR=$(dirname -- "$( readlink -f -- "$0"; )";)

docker-compose \
  --file ${SCRIPT_DIR}/${EXPERIMENT_NAME}.yml \
  --env-file ${SCRIPT_DIR}/baseline-attack.env \
  --project-name ${EXPERIMENT_NAME} \
  ${DOCKER_COMPOSE_COMMAND}
