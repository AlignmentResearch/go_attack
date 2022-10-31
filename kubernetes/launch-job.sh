#!/bin/bash -e

####################
# Argument parsing #
####################

DEFAULT_NUM_GPUS=4

usage() {
  echo "Usage: $0 [--gpus GPUS] [--max-victimplay-gpus GPUS] [--match]"
  echo "         [--num-match-games NUM_MATCH_GAMES] [--use-weka] PREFIX"
  echo
  echo "positional arguments:"
  echo "  PREFIX  Identifying label used for the name of the job and the name"
  echo "          of the output directory."
  echo
  echo "optional arguments:"
  echo "  -g GPUS, --gpus GPUS"
  echo "    Minimum number of GPUs to use for the victimplay/match game loop."
  echo "    default: ${DEFAULT_NUM_GPUS}"
  echo "  -m GPUS, --max-victimplay-gpus GPUS"
  echo "    Maximum number of GPUs to use for the victimplay game loop."
  echo "    (Only for victimplay, not match.)"
  echo "    default: twice the minimum number of GPUs."
  echo "  --num-match-games NUM_MATCH_GAMES"
  echo "    Number of match games to play."
  echo "    (Only for match, not victimplay.)"
  echo "  --match"
  echo "    Run match instead of victimplay."
  echo "  -w, --use-weka"
  echo "    Store results on the go-attack Weka volume instead of the CHAI NAS"
  echo "    volume."
  echo
  echo "Optional arguments should be specified before positional arguments."
}

NUM_POSITIONAL_ARGUMENTS=1

MIN_GPUS=${DEFAULT_NUM_GPUS}
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while [ "$#" -gt ${NUM_POSITIONAL_ARGUMENTS} ]; do
  case $1 in
    -h|--help) usage; exit 0 ;;
    -g|--gpus) MIN_GPUS=$2; shift ;;
    -m|--victimplay-max-gpus) MAX_VICTIMPLAY_GPUS=$2; shift ;;
    --match) MATCH=1 ;;
    --num-match-games) NUM_MATCH_GAMES=$2; shift ;;
    -w|--use-weka) USE_WEKA=1 ;;
    *) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
  esac
  shift
done

if [ $# -ne ${NUM_POSITIONAL_ARGUMENTS} ]; then
  usage
  exit 1
fi

MAX_VICTIMPLAY_GPUS=${MAX_VICTIMPLAY_GPUS:-$((2*MIN_GPUS))}

############################
# Launching the experiment #
############################

GIT_ROOT=$(git rev-parse --show-toplevel)
RUN_NAME="$1-$(date +%Y%m%d-%H%M%S)"
echo "Run name: $RUN_NAME"

# Make sure we don't miss any changes
if [ "$(git status --porcelain --untracked-files=no | wc -l)" -gt 0 ]; then
    echo "Git repo is dirty, aborting" 1>&2
    exit 1
fi

if [ -n "${USE_WEKA}" ]; then
  VOLUME_FLAGS="--volume-name go-attack --volume-mount /shared"
else
  VOLUME_FLAGS="--shared-host-dir /nas/ucb/k8/go-attack --shared-host-dir-mount /shared"
fi
VOLUME_NAME="shared"

if [ -n "${MATCH}" ]; then
  IMAGE_TYPES="--image cpp"
else
  IMAGE_TYPES="--image cpp --image python"
fi

# Maybe build and push new Docker images
# shellcheck disable=SC2086
python "$GIT_ROOT"/kubernetes/update_images.py ${IMAGE_TYPES}
# Load the env variables just created by update_images.py
# This line is weird because ShellCheck wants us to put double quotes around the
# $() context but this changes the behavior to something we don't want
# shellcheck disable=SC2046
export $(grep -v '^#' "$GIT_ROOT"/kubernetes/active-images.env | xargs)

if [ -n "${MATCH}" ]; then
  if [ -n "${NUM_MATCH_GAMES}" ]; then
    GAMES_PER_REPLICA=$(((NUM_MATCH_GAMES + MIN_GPUS - 1) / MIN_GPUS))
  fi
  # shellcheck disable=SC2086
  ctl job run --container \
    "$CPP_IMAGE" \
    $VOLUME_FLAGS \
    --command "/go_attack/kubernetes/match.sh /shared/match/${RUN_NAME} ${NUM_GAMES} ${GAMES_PER_REPLICA}" \
    --gpu 1 \
    --name go-match-"$1" \
    --replicas "${MIN_GPUS}"
  exit 0
fi

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
    --replicas "${MIN_GPUS}" 1 1 1 1

EXTRA_VICTIMPLAY_GPUS=$((MAX_VICTIMPLAY_GPUS-MIN_GPUS))
# shellcheck disable=SC2086
ctl job run --container \
    "$CPP_IMAGE" \
    $VOLUME_FLAGS \
    --command "/go_attack/kubernetes/victimplay.sh $RUN_NAME $VOLUME_NAME" \
    --gpu 1 \
    --name go-training-"$1"-victimplay \
    --replicas "${EXTRA_VICTIMPLAY_GPUS}"
