#!/bin/bash

# Directory of this script
SCRIPT_DIR=$(dirname -- "$( readlink -f -- "$0"; )";)
ENV_FILE=${SCRIPT_DIR}/baseline-attack.env
export VICTIM_GPU=0

function usage() {
  echo "Usage: $0 [-e ENV_FILE] [-g GPU] [-l LABEL] EXPERIMENT COMMAND"
  echo
  echo "Launches a transfer experiment."
  echo
  echo "optional arguments:"
  echo "  -e ENV_FILE, --env-file ENV_FILE"
  echo "              Which file to use for environment variables."
  echo "              default: ${ENV_FILE}"
  echo "  -g GPU, --victim-gpu GPU"
  echo "              Which GPU to run the victim on."
  echo "              default: ${VICTIM_GPU}"
  echo "  -l LABEL, --label LABEL"
  echo "              Label attached to the output directory and docker-compose"
  echo "              project-name. If you are running multiple instances of"
  echo "              the same experiment concurrently, you should specify"
  echo "              unique labels for each instance so the docker-compose"
  echo "              instances don't interfere with each other."
  echo
  echo "positional arguments:"
  echo "  EXPERIMENT  Which experiment to run."
  echo "              values: {baseline-attack-vs-elf, baseline-attack-vs-leela}"
  echo "  COMMAND     docker-compose command to run."
  echo "              values: {build, up}"
  echo
  echo "Optional arguments should be specified before positional arguments."
}

NUM_POSITIONAL_ARGUMENTS=2

# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while [[ "$#" -gt ${NUM_POSITIONAL_ARGUMENTS} ]]; do
  case $1 in
    -e|--env-file) ENV_FILE=$2; shift ;;
    -g|--victim-gpu) VICTIM_GPU=$2; shift ;;
    -l|--label) LABEL=$2; shift ;;
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
export HOST_OUTPUT_DIR=${HOST_REPO_ROOT}/transfer-logs/${EXPERIMENT_NAME}/
[[ -n "${LABEL}" ]] && HOST_OUTPUT_DIR+="${LABEL}-"
HOST_OUTPUT_DIR+=$(date +%Y%m%d-%H%M%S)
mkdir --parents ${HOST_OUTPUT_DIR}

if [ ${EXPERIMENT_NAME} = "baseline-attack-vs-leela" ]; then
  export HOST_LEELA_TUNING_FILE=${HOST_REPO_ROOT}/engines/leela/leelaz_opencl_tuning
  # Make sure $HOST_LEELA_TUNING_FILE exists.
  touch -a ${HOST_LEELA_TUNING_FILE}
fi

docker-compose \
  --file ${SCRIPT_DIR}/${EXPERIMENT_NAME}.yml \
  --env-file ${ENV_FILE} \
  --project-name ${EXPERIMENT_NAME}-${LABEL} \
  ${DOCKER_COMPOSE_COMMAND}
