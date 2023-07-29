#!/bin/bash -eu

HOST_REPO_ROOT=$(git rev-parse --show-toplevel)

DEFAULT_NUM_CPUS=8
DEFAULT_NUM_GAMES=100
DEFAULT_NUM_GPUS=1
DEFAULT_ADV_CONFIG=/go_attack/configs/gtp-amcts.cfg
DEFAULT_VICTIM_CONFIG=/go_attack/configs/gtp-raw.cfg
DEFAULT_ADV_MODEL=/shared/victimplay/ttseng-avoid-pass-alive-coldstart-39-20221025-175949/models/t0-s545065216-d136760487/model.bin.gz
DEFAULT_VICTIM_MODEL=/shared/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz

usage() {
  echo "Schedules a job that plays a victim (on KataGo-raw) against an A-MCTS"
  echo "adversary via GTP."
  echo
  echo "Usage: $0 [--cpus CPUS] [--gpus GPUS] [--games NUM_GAMES]"
  echo "         [--adv-config ADV_CONFIG] [--victim-config VICTIM_CONFIG]"
  echo "         [--adv-config ADV_MODEL] [--victim-config VICTIM_MODEL] PREFIX"
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
  echo "    default: ${DEFAULT_NUM_GAMES}"
  echo
  echo "  --adv-config ADV_CONFIG"
  echo "              Config for adversary to use."
  echo "              default: ${DEFAULT_ADV_CONFIG}"
  echo "  --victim-config VICTIM_CONFIG"
  echo "              Config for victim to use."
  echo "              default: ${DEFAULT_VICTIM_CONFIG}"
  echo "  --adv-model ADV_MODEL"
  echo "              Model for adversary to use."
  echo "              default: ${DEFAULT_ADV_MODEL}"
  echo "  --victim-model VICTIM_MODEL"
  echo "              Model for victim to use."
  echo "              default: ${DEFAULT_VICTIM_MODEL}"
  echo
  echo "Optional arguments should be specified before positional arguments."
}

NUM_CPUS=${DEFAULT_NUM_CPUS}
NUM_GAMES=${DEFAULT_NUM_GAMES}
NUM_GPUS=${DEFAULT_NUM_GPUS}
ADV_CONFIG=${DEFAULT_ADV_CONFIG}
VICTIM_CONFIG=${DEFAULT_VICTIM_CONFIG}
ADV_MODEL=${DEFAULT_ADV_MODEL}
VICTIM_MODEL=${DEFAULT_VICTIM_MODEL}
while [ -n "${1-}" ]; do
  case $1 in
    -h|--help) usage; exit 0 ;;
    --cpus) NUM_CPUS=$2; shift ;;
    -g|--gpus) NUM_GPUS=$2; shift ;;
    -n|--games) NUM_GAMES=$2; shift ;;
    --adv-config) ADV_CONFIG=$2; shift ;;
    --victim-config) VICTIM_CONFIG=$2; shift ;;
    --adv-model) ADV_MODEL=$2; shift ;;
    --victim-model) VICTIM_MODEL=$2; shift ;;
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
# Job name is prefixed with "gg", meaning "go-gtp".
# shellcheck disable=SC2086
ctl job run --container \
  "$CPP_AND_TWOGTP_IMAGE" \
  $VOLUME_FLAGS \
  --command "bash -x
  /go_attack/kubernetes/gtp-eval.sh
  /shared/gtp-eval/$RUN_NAME $NUM_GPUS $NUM_GAMES
  $ADV_CONFIG $VICTIM_CONFIG $ADV_MODEL $VICTIM_MODEL" \
  --high-priority \
  --gpu "$NUM_GPUS" \
  --cpu "$NUM_CPUS" \
  --name "gg-$1" \
  --replicas 1
