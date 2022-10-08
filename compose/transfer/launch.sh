#!/bin/bash

####################
# Argument parsing #
####################

# Exported variables like these are used inside the docker-compose yml file.
export HOST_REPO_ROOT=$(git rev-parse --show-toplevel)

DEFAULT_GPUS_STR="all"
DEFAULT_NUM_GAMES_TOTAL=100
DEFAULT_NUM_THREADS=16

function usage() {
  echo "Usage: $0 [-g GPUS] [-l LABEL] [-n NUM_GAMES] [-o OUTPUT_DIR] [-t NUM_THREADS] EXPERIMENT COMMAND"
  echo
  echo "Launches a transfer experiment."
  echo
  echo "optional arguments:"
  echo "  -g GPUS, --gpus GPUS"
  echo "              Which GPUs to run the victim on. This can be a"
  echo "              comma-separated list (with no spaces in between) or"
  echo "              'all'."
  echo "              default: ${DEFAULT_GPUS_STR}"
  echo "  -l LABEL, --label LABEL"
  echo "              Label attached to the output directory and docker-compose"
  echo "              project-name. If you are running multiple instances of"
  echo "              the same experiment concurrently, you should specify"
  echo "              unique labels for each instance so the docker-compose"
  echo "              instances don't interfere with each other."
  echo "  -n NUM_GAMES, --num-games NUM_GAMES"
  echo "              The total number of games to be played."
  echo "              default: ${DEFAULT_NUM_GAMES_TOTAL}"
  echo "  -o OUTPUT_DIR, --output-dir OUTPUT_DIR"
  echo "              The directory to which to output SGFs and logs."
  echo "              default: ${HOST_REPO_ROOT}/transfer-logs/<experiment>/<label>-<date>"
  echo "  -t NUM_THREADS, --num-threads NUM_THREADS"
  echo "              The number of games to be played at once."
  echo "              default: ${DEFAULT_NUM_THREADS}"
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

GPUS_STR=${DEFAULT_GPUS_STR}
NUM_GAMES_TOTAL=${DEFAULT_NUM_GAMES_TOTAL}
NUM_THREADS=${DEFAULT_NUM_THREADS}
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while [[ "$#" -gt ${NUM_POSITIONAL_ARGUMENTS} ]]; do
  case $1 in
    -g|--gpus) GPUS_STR=$2; shift ;;
    -l|--label) LABEL=$2; shift ;;
    -o|--output-dir) HOST_BASE_OUTPUT_DIR=$2; shift ;;
    -n|--num-games) NUM_GAMES_TOTAL=$2; shift ;;
    -t|--num-threads) NUM_THREADS=$2; shift ;;
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

GPUS=()
if [[ "${GPUS_STR}" == "all" ]]; then
  NUM_GPUS=$(nvidia-smi --list-gpus | wc -l)
  echo "Number of GPUs detected: ${NUM_GPUS}"
  for (( i = 0; i < NUM_GPUS; i++)) ; do
    GPUS+=($i)
  done
else
  for i in ${GPUS_STR//,/ }; do  # parse comma-separated string
    GPUS+=($i)
  done
fi

############################
# Launching the experiment #
############################

# Directory of this script
SCRIPT_DIR=$(dirname -- "$( readlink -f -- "$0"; )";)

if [[ "${DOCKER_COMPOSE_COMMAND}" != "up" ]]; then
  docker-compose --file ${SCRIPT_DIR}/${EXPERIMENT_NAME}.yml \
    ${DOCKER_COMPOSE_COMMAND}
  exit 0
fi

if [[ -z "${HOST_BASE_OUTPUT_DIR}" ]]; then
  HOST_BASE_OUTPUT_DIR=${HOST_REPO_ROOT}/transfer-logs/${EXPERIMENT_NAME}/
  [[ -n "${LABEL}" ]] && HOST_BASE_OUTPUT_DIR+="${LABEL}-"
  HOST_BASE_OUTPUT_DIR+=$(date +%Y%m%d-%H%M%S)
fi

if [[ "${EXPERIMENT_NAME}" = "baseline-attack-vs-leela" ]]; then
  export HOST_LEELA_TUNING_FILE=${HOST_REPO_ROOT}/engines/leela/leelaz_opencl_tuning
  # Make sure $HOST_LEELA_TUNING_FILE exists.
  touch -a ${HOST_LEELA_TUNING_FILE}
fi

PROJECT_NAME_PREFIX=${EXPERIMENT_NAME}-${LABEL}-thread
for (( thread_idx = 0; thread_idx < NUM_THREADS; thread_idx++)) ; do
  export HOST_OUTPUT_DIR=${HOST_BASE_OUTPUT_DIR}/thread${thread_idx}
  mkdir --parents ${HOST_OUTPUT_DIR}
  export NUM_GAMES=$(($NUM_GAMES_TOTAL / $NUM_THREADS + ($thread_idx < ($NUM_GAMES_TOTAL % $NUM_THREADS))))
  GPU_LEN=${#GPUS[@]}
  export GPU=${GPUS[(($thread_idx % $GPU_LEN))]}
  # We don't want multiple threads racing to write to shared files.
  export ARE_SHARED_FILES_READ_ONLY=$([[ $thread_idx -eq "0" ]] && echo "false" || echo "true")

  docker-compose ${DOCKER_FLAGS} \
    --file ${SCRIPT_DIR}/${EXPERIMENT_NAME}.yml \
    --project-name ${PROJECT_NAME_PREFIX}${thread_idx} \
    ${DOCKER_COMPOSE_COMMAND} --abort-on-container-exit &
done

wait $(jobs -p)

# We need to clean up the networks created by all the many docker-compose calls
# or else Docker might later run out of addresses, giving an error:
#   ERROR: could not find an available, non-overlapping IPv4 address pool among
#   the defaults to assign to the network
docker network rm $(docker network ls | grep "${PROJECT_NAME_PREFIX}" | awk '{print $1;}')
