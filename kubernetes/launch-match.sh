#!/bin/bash -e

####################
# Argument parsing #
####################

DEFAULT_NUM_MATCH_GPUS=8

usage() {
  echo "Usage: $0 [--gpus GPUS] PREFIX VICTIM ADVERSARY"
  echo
  echo "positional arguments:"
  echo "  PREFIX    Identifying label used for the name of the job and the name"
  echo "            of the output directory."
  echo "  VICTIM    Filename of the victim network to use."
  echo "  ADVERSARY Filename of the adversary network to use."
  echo
  echo "optional arguments:"
  echo "  -g GPUS, --gpus GPUS"
  echo "    Number of GPUs to use for match."
  echo "    default: ${DEFAULT_NUM_MATCH_GPUS}"
  echo
  echo "Optional arguments should be specified before positional arguments."
}

NUM_POSITIONAL_ARGUMENTS=3
NUM_GPUS=${DEFAULT_NUM_MATCH_GPUS}

# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while [ "$#" -gt ${NUM_POSITIONAL_ARGUMENTS} ]; do
  case $1 in
    -h|--help) usage; exit 0 ;;
    -g|--gpus) NUM_GPUS=$2; shift ;;
    *) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
  esac
  shift
done

if [ $# -ne ${NUM_POSITIONAL_ARGUMENTS} ]; then
  usage
  exit 1
fi

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

# Maybe build and push new Docker images
python "$GIT_ROOT"/kubernetes/update_images.py
# Load the env variables just created by update_images.py
# This line is weird because ShellCheck wants us to put double quotes around the
# $() context but this changes the behavior to something we don't want
# shellcheck disable=SC2046
export $(grep -v '^#' "$GIT_ROOT"/kubernetes/active-images.env | xargs)

ADVERSARY_PATH="$3"
VICTIM_PATH=/shared/victims/"$2"

# shellcheck disable=SC2215,SC2086,SC2089,SC2090
ctl job run --container \
    "$CPP_IMAGE" \
    --volume-name go-attack \
    --volume-mount /shared \
    --command "/go_attack/kubernetes/match.sh $VICTIM_PATH $ADVERSARY_PATH" \
    --gpu 1 \
    --name go-match-"$RUN_NAME" \
    --replicas "${NUM_GPUS}"
