#!/bin/bash -eu

DEFAULT_NUM_CPUS=8
DEFAULT_NUM_GAMES=100
DEFAULT_NUM_GPUS=1

usage() {
  echo "Schedules a job that plays a victim (on KataGo-raw) against an A-MCTS"
  echo "adversary via GTP."
  echo
  echo "Usage: $0 [--cpus CPUS] [--gpus GPUS] [--games NUM_GAMES] [--use-weka] PREFIX"
  echo
  echo "positional arguments:"
  echo "  PREFIX     Identifying label used for the name of the job and the name"
  echo "             of the output directory."
  echo
  echo "optional arguments:"
  echo "  --cpus CPUS"
  echo "    Number of GPUs to use."
  echo "    default: ${DEFAULT_NUM_CPUS}"
  echo "  -g GPUS, --gpus GPUS"
  echo "    Number of GPUs to use."
  echo "    default: ${DEFAULT_NUM_GPUS}"
  echo "  -n NUM_GAMES, --games NUM_GAMES"
  echo "    Number of games to play."
  echo "  -w, --use-weka"
  echo "    Store results on the go-attack Weka volume instead of the CHAI NAS"
  echo "    volume."
  echo
  echo "Optional arguments should be specified before positional arguments."
}

NUM_CPUS=${DEFAULT_NUM_CPUS}
NUM_GAMES=${DEFAULT_NUM_GAMES}
NUM_GPUS=${DEFAULT_NUM_GPUS}
while [ -n "${1-}" ]; do
  case $1 in
    -h|--help) usage; exit 0 ;;
    --cpus) NUM_CPUS=$2; shift ;;
    -g|--gpus) NUM_GPUS=$2; shift ;;
    -n|--games) NUM_GAMES=$2; shift ;;
    -w|--use-weka) export USE_WEKA=1 ;;
    *) break ;;
  esac
  shift
done

NUM_POSITIONAL_ARGUMENTS=1
if [ $# -ne ${NUM_POSITIONAL_ARGUMENTS} ]; then
  usage
  exit 1
fi

RUN_NAME="$1-$(date +%Y%m%d-%H%M%S)"
echo "Run name: $RUN_NAME"

source "$(dirname "$(readlink -f "$0")")"/launch-common.sh
update_images cpp-and-twogtp

# We have 1 replica with lots of GPUS instead of several replicas with 1 GPU,
# because if we do an expensive evaluations with high visit count, we'd prefer
# having games run sequentially quickly instead of games run in parallel slowly.
# If we run slow games in parallel, we're likely to lose a lot of progress if
# the job gets interrupted.
# shellcheck disable=SC2086
ctl job run --container \
  "$CPP_AND_TWOGTP_IMAGE" \
  $VOLUME_FLAGS \
  --command "bash -x
  /go_attack/kubernetes/gtp-eval.sh
  /shared/eval/$RUN_NAME $NUM_GPUS" \
  --high-priority \
  --gpu "$NUM_GPUS" \
  --cpu "$NUM_CPUS" \
  --name "go-gtp-$PREFIX" \
  --replicas 1
