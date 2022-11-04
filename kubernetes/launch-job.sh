#!/bin/bash -e

####################
# Argument parsing #
####################

DEFAULT_NUM_VICTIMPLAY_GPUS=4

usage() {
  echo "Usage: $0 [--victimplay-gpus GPUS] [--use-weka] PREFIX"
  echo
  echo "positional arguments:"
  echo "  PREFIX  Identifying label used for the name of the job and the name"
  echo "          of the output directory."
  echo
  echo "optional arguments:"
  echo "  -g GPUS, --victimplay-gpus GPUS"
  echo "    Minimum number of GPUs to use for victimplay."
  echo "    default: ${DEFAULT_NUM_VICTIMPLAY_GPUS}"
  echo "  -m GPUS, --victimplay-max-gpus GPUS"
  echo "    Maximum number of GPUs to use for victimplay."
  echo "    default: twice the minimum number of GPUs."
  echo "  -w, --use-weka"
  echo "    Store results on the go-attack Weka volume instead of the CHAI NAS"
  echo "    volume."
  echo
  echo "Optional arguments should be specified before positional arguments."
}

NUM_POSITIONAL_ARGUMENTS=1

MIN_VICTIMPLAY_GPUS=${DEFAULT_NUM_VICTIMPLAY_GPUS}
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while [ "$#" -gt ${NUM_POSITIONAL_ARGUMENTS} ]; do
  case $1 in
    -h|--help) usage; exit 0 ;;
    -g|--victimplay-gpus) MIN_VICTIMPLAY_GPUS=$2; shift ;;
    -m|--victimplay-max-gpus) MAX_VICTIMPLAY_GPUS=$2; shift ;;
    -w|--use-weka) export USE_WEKA=1 ;;
    *) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
  esac
  shift
done

if [ $# -ne ${NUM_POSITIONAL_ARGUMENTS} ]; then
  usage
  exit 1
fi

MAX_VICTIMPLAY_GPUS=${MAX_VICTIMPLAY_GPUS:-$((2*MIN_VICTIMPLAY_GPUS))}

############################
# Launching the experiment #
############################

RUN_NAME="$1-$(date +%Y%m%d-%H%M%S)"
echo "Run name: $RUN_NAME"

source "$(dirname "$(readlink -f "$0")")"/launch-common.sh
VOLUME_NAME="shared"

# shellcheck disable=SC2215,SC2086,SC2089,SC2090
ctl job run --container \
    "$CPP_IMAGE" \
    "$CPP_IMAGE" \
    "$PYTHON_IMAGE" \
    "$PYTHON_IMAGE" \
    "$PYTHON_IMAGE" \
    $VOLUME_FLAGS \
    --command "/go_attack/kubernetes/victimplay.sh $RUN_NAME $VOLUME_NAME" \
    "/engines/KataGo-custom/cpp/evaluate_loop.sh /$VOLUME_NAME/victimplay/$RUN_NAME" \
    "/go_attack/kubernetes/train.sh $RUN_NAME $VOLUME_NAME" \
    "/go_attack/kubernetes/shuffle-and-export.sh $RUN_NAME $RUN_NAME $VOLUME_NAME" \
    "/go_attack/kubernetes/curriculum.sh $RUN_NAME $VOLUME_NAME" \
    --high-priority \
    --gpu 1 1 1 0 0 \
    --name go-training-"$1"-essentials \
    --replicas "${MIN_VICTIMPLAY_GPUS}" 1 1 1 1

EXTRA_VICTIMPLAY_GPUS=$((MAX_VICTIMPLAY_GPUS-MIN_VICTIMPLAY_GPUS))
# shellcheck disable=SC2086
ctl job run --container \
    "$CPP_IMAGE" \
    $VOLUME_FLAGS \
    --command "/go_attack/kubernetes/victimplay.sh $RUN_NAME $VOLUME_NAME" \
    --gpu 1 \
    --name go-training-"$1"-victimplay \
    --replicas "${EXTRA_VICTIMPLAY_GPUS}"
