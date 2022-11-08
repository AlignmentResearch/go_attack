#!/bin/bash -e

####################
# Argument parsing #
####################

DEFAULT_NUM_VICTIMPLAY_GPUS=4

usage() {
  echo "Usage: $0 [--victimplay-gpus GPUS] [--victimplay-max-gpus MAX_GPUS]"
  echo "         [--resume TIMESTAMP] [--use-weka] PREFIX"
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
  echo "  -r, --resume TIMESTAMP"
  echo "    Resume a previous run. If this flag is given, the PREFIX argument"
  echo "    must exactly be match the run to be resumed, and the TIMESTAMP"
  echo "    argument should match the timestamp attached to the name of the"
  echo "    previous run's output directory. The use of the --use-weka flag"
  echo "    must also exactly match that of the previous run."
  echo "  -w, --use-weka"
  echo "    Store results on the go-attack Weka volume instead of the CHAI NAS"
  echo "    volume."
  echo
  echo "Optional arguments should be specified before positional arguments."
}

MIN_VICTIMPLAY_GPUS=${DEFAULT_NUM_VICTIMPLAY_GPUS}
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while true; do
  case $1 in
    -h|--help) usage; exit 0 ;;
    -g|--victimplay-gpus) MIN_VICTIMPLAY_GPUS=$2; shift ;;
    -m|--victimplay-max-gpus) MAX_VICTIMPLAY_GPUS=$2; shift ;;
    -r|--resume) RESUME_TIMESTAMP=$2; shift ;;
    -w|--use-weka) USE_WEKA=1 ;;
    -*) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
    *) break ;;
  esac
  shift
done

NUM_POSITIONAL_ARGUMENTS=1
if [ $# -ne ${NUM_POSITIONAL_ARGUMENTS} ]; then
  usage
  exit 1
fi

MAX_VICTIMPLAY_GPUS=${MAX_VICTIMPLAY_GPUS:-$((2*MIN_VICTIMPLAY_GPUS))}

############################
# Launching the experiment #
############################

GIT_ROOT=$(git rev-parse --show-toplevel)
RUN_NAME="$1-${RESUME_TIMESTAMP:-$(date +%Y%m%d-%H%M%S)}"
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

if [ -n "${USE_WEKA}" ]; then
  VOLUME_FLAGS="--volume-name go-attack --volume-mount /shared"
else
  VOLUME_FLAGS="--shared-host-dir /nas/ucb/k8/go-attack --shared-host-dir-mount /shared"
fi
VOLUME_NAME="shared"

# note: shortening -essentials + -victimplay to -e + -v in the job names or else
# I hit the 63-char limit on job names
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
    --name go-train-"$1"-vital \
    --replicas "${MIN_VICTIMPLAY_GPUS}" 1 1 1 1

EXTRA_VICTIMPLAY_GPUS=$((MAX_VICTIMPLAY_GPUS-MIN_VICTIMPLAY_GPUS))
# shellcheck disable=SC2086
ctl job run --container \
    "$CPP_IMAGE" \
    $VOLUME_FLAGS \
    --command "/go_attack/kubernetes/victimplay.sh $RUN_NAME $VOLUME_NAME" \
    --gpu 1 \
    --name go-train-"$1"-extra \
    --replicas "${EXTRA_VICTIMPLAY_GPUS}"
