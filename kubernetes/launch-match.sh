#!/bin/bash -e

####################
# Argument parsing #
####################

DEFAULT_NUM_GPUS=1

usage() {
  echo "Schedules a job that runs \`match\`."
  echo
  echo "Usage: $0 [--gpus GPUS] [--games NUM_GAMES] [--use-weka] PREFIX"
  echo "          [--EXTRA_MATCH_FLAGS]"
  echo
  echo "positional arguments:"
  echo "  PREFIX     Identifying label used for the name of the job and the name"
  echo "             of the output directory."
  echo
  echo "optional arguments:"
  echo "  -g GPUS, --gpus GPUS"
  echo "    Number of GPUs to use."
  echo "    default: ${DEFAULT_NUM_GPUS}"
  echo "  -n NUM_GAMES, --games NUM_GAMES"
  echo "    Number of match games to play. If not specified, then the number of"
  echo "    games will be the numGamesTotal specified in the \`match\` config"
  echo "    multiplied by the number of GPUs."
  echo "  -w, --use-weka"
  echo "    Store results on the go-attack Weka volume instead of the CHAI NAS"
  echo "    volume."
  echo
  echo "Optional arguments should be specified before positional arguments."
  echo
  echo "Extra flags to \`match\` can be specified by adding them after the"
  echo "positional arguments with \"--\" in between, e.g.,"
  echo "  $0 test-run -- -override-config nnModelFile0=/dev/null"
}

NUM_POSITIONAL_ARGUMENTS=1

NUM_GPUS=${DEFAULT_NUM_GPUS}
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while true; do
  case $1 in
    -h|--help) usage; exit 0 ;;
    -g|--gpus) NUM_GPUS=$2; shift ;;
    -n|--games) NUM_GAMES=$2; shift ;;
    -w|--use-weka) export USE_WEKA=1 ;;
    *) break ;;
  esac
  shift
done

if [ $# -lt ${NUM_POSITIONAL_ARGUMENTS} ]; then
  usage
  exit 1
fi

PREFIX=$1
RUN_NAME="$PREFIX-$(date +%Y%m%d-%H%M%S)"
echo "Run name: $RUN_NAME"
shift 1

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

# shellcheck disable=SC1091
source "$(dirname "$(readlink -f "$0")")"/launch-common.sh
update_images cpp

if [ -n "${NUM_GAMES}" ]; then
  GAMES_PER_REPLICA=$(((NUM_GAMES + NUM_GPUS - 1) / NUM_GPUS))
else
  GAMES_PER_REPLICA=-1
fi

# shellcheck disable=SC2086
ctl job run --container \
  "$CPP_IMAGE" \
  $VOLUME_FLAGS \
  --command "bash -x
  /go_attack/kubernetes/match.sh
  /shared/match/${RUN_NAME}
  ${GAMES_PER_REPLICA}
  $*" \
  --high-priority \
  --gpu 1 \
  --name go-match-"$PREFIX" \
  --replicas "${NUM_GPUS}"
