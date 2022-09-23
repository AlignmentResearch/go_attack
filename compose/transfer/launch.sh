#!/bin/bash

# Directory of this script
SCRIPT_DIR=$(dirname -- "$( readlink -f -- "$0"; )";)
ENV_FILE=${SCRIPT_DIR}/baseline-attack.env

function usage() {
  echo "Usage: $0 [-e env_file] experiment command"
  echo
  echo "Launches a transfer experiment."
  echo
  echo "optional arguments:"
  echo "  -e env_file, --env-file env_file"
  echo "              Which file to use for environment variables."
  echo "              default: ${ENV_FILE}"
  echo
  echo "positional arguments:"
  echo "  experiment  Which experiment to run."
  echo "              values: {baseline-attack-vs-elf, baseline-attack-vs-leela}"
  echo "  command     docker-compose command to run."
  echo "              values: {build, up}"
  echo
  echo "Optional arguments should be specified before positional arguments."
}

NUM_POSITIONAL_ARGUMENTS=2

# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while [[ "$#" -gt ${NUM_POSITIONAL_ARGUMENTS} ]]; do
  case $1 in
    -e|--env-file) ENV_FILE=$2; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
  esac
  shift
done

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

docker-compose \
  --file ${SCRIPT_DIR}/${EXPERIMENT_NAME}.yml \
  --env-file ${ENV_FILE} \
  --project-name ${EXPERIMENT_NAME} \
  ${DOCKER_COMPOSE_COMMAND}
