#!/bin/bash -e

####################
# Argument parsing #
####################

DEFAULT_NUM_GPUS=4
DEFAULT_NUM_GAMES=1000

usage() {
  echo "Usage: $0 [--gpus GPUS] [--games NUM_GAMES] [--use-weka] PREFIX"
  echo
  echo "positional arguments:"
  echo "  PREFIX  Identifying label used for the name of the job and the name"
  echo "          of the output directory."
  echo
  echo "optional arguments:"
  echo "  -g GPUS, --gpus GPUS"
  echo "    Number of GPUs to use."
  echo "    default: ${DEFAULT_NUM_GPUS}"
  echo "  -n NUM_GAMES, --games NUM_GAMES"
  echo "    Number of match games to play."
  echo "    default: ${DEFAULT_NUM_GAMES}"
  echo "  -w, --use-weka"
  echo "    Store results on the go-attack Weka volume instead of the CHAI NAS"
  echo "    volume."
  echo
  echo "Optional arguments should be specified before positional arguments."
}

NUM_POSITIONAL_ARGUMENTS=1

NUM_GPUS=${DEFAULT_NUM_GPUS}
NUM_GAMES=${DEFAULT_NUM_GAMES}
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while true; do
  case $1 in
    -h|--help) usage; exit 0 ;;
    -g|--gpus) NUM_GPUS=$2; shift ;;
    -n|--games) NUM_GAMES=$2; shift ;;
    -w|--use-weka) USE_WEKA=1 ;;
    *) break ;;
  esac
  shift
done

if [ $# -lt ${NUM_POSITIONAL_ARGUMENTS} ]; then
  usage
  exit 1
fi

RUN_NAME="$1-$(date +%Y%m%d-%H%M%S)"
echo "Run name: $RUN_NAME"
shift

if [ $# -gt 0 ]; then
  if [ "$1" != "--" ]; then
    echo "Unexpected arguments: $*"
    usage
    exit 1
  fi
  shift
  # remaining arguments are treated as extra arguments to `match`
fi

############################
# Launching the experiment #
############################

GIT_ROOT=$(git rev-parse --show-toplevel)

# Make sure we don't miss any changes
if [ "$(git status --porcelain --untracked-files=no | wc -l)" -gt 0 ]; then
    echo "Git repo is dirty, aborting" 1>&2
    exit 1
fi

# Maybe build and push new Docker images
python "$GIT_ROOT"/kubernetes/update_images.py --image cpp
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


GAMES_PER_REPLICA=$(((NUM_MATCH_GAMES + NUM_GPUS - 1) / NUM_GPUS))
# shellcheck disable=SC2086
ctl job run --container \
  "$CPP_IMAGE" \
  $VOLUME_FLAGS \
  --command "/go_attack/kubernetes/match.sh /shared/match/${RUN_NAME} ${NUM_GAMES} ${GAMES_PER_REPLICA} $*" \
  --gpu 1 \
  --name go-match-"$1" \
  --replicas "${NUM_GPUS}"
exit 0
