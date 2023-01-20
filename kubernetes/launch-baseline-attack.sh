#!/bin/bash -eu

DEFAULT_NUM_GPUS=4

usage() {
  echo "Usage: $0 [--gpus GPUS] [--games NUM_GAMES] [--use-weka] PREFIX"
  echo
  echo "positional arguments:"
  echo "  PREFIX     Identifying label used for the name of the job and the name"
  echo "             of the output directory."
  echo
  echo "optional arguments:"
  echo "  -g GPUS, --gpus GPUS"
  echo "    Number of GPUs to use."
  echo "    default: ${DEFAULT_NUM_GPUS}"
  echo "  -w, --use-weka"
  echo "    Store results on the go-attack Weka volume instead of the CHAI NAS"
  echo "    volume."
  echo
  echo "Optional arguments should be specified before positional arguments."
}

NUM_GPUS=${DEFAULT_NUM_GPUS}
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while [ -n "${1-}" ]; do
  case $1 in
    -h|--help) usage; exit 0 ;;
    -g|--gpus) NUM_GPUS=$2; shift ;;
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
RUN_DIR="/shared/baseline-attack/$RUN_NAME"

source "$(dirname "$(readlink -f "$0")")"/launch-common.sh
update_images cpp

# shellcheck disable=SC2086
ctl job run --container \
  "$CPP_IMAGE" \
  $VOLUME_FLAGS \
  --command "/go_attack/kubernetes/baseline-attack.sh
  $RUN_DIR 2>&1 | tee $RUN_DIR/baseline-attack.log" \
  --high-priority \
  --gpu "$NUM_GPUS" \
  --name "go-baseline-$1" \
  --replicas 1
