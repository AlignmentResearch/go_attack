#!/bin/bash -eu

source "$(dirname "$0")"/common.sh

WARMSTART_FLAG=
# The command line flags have same meaning as in from kubernetes/victimplay.sh.
while [ -n "${1-}" ]; do
  case $1 in
    --warmstart) WARMSTART_FLAG="--warmstart"; ;;
    -*) echo "Unknown parameter passed: $1"; exit 1 ;;
    *) break ;;
  esac
  shift
done

RUN_NAME="$1"
VOLUME_NAME="$2"
ALTERNATE_ITERATION_FIRST="$3"

ITERATION=-1
while true; do
  ITERATION=$((ITERATION + 1))
  echo "Starting iteration $ITERATION"

  if [ $((ITERATION % 2)) -eq "$ALTERNATE_ITERATION_FIRST" ]; then
    CONFIG=/ANONYMOUS_REPO/configs/active-experiment.cfg
  else
    CONFIG=/ANONYMOUS_REPO/configs/iterated-training/alternate-experiment.cfg
  fi

  ITERATION_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/iteration-"$ITERATION"
  run_until_curriculum_done "$ITERATION_DIR" \
    /ANONYMOUS_REPO/kubernetes/victimplay.sh --config "$CONFIG" "$WARMSTART_FLAG" \
    "$RUN_NAME"/iteration-"$ITERATION" "$VOLUME_NAME"

  # All iterations besides the first are warmstarted with the victim of the
  # previous iteration.
  WARMSTART_FLAG="--warmstart"
done
