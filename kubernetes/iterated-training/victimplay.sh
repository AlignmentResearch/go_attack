#!/bin/bash -eu

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

source $(dirname $0)/common.sh

ITERATION=-1
while true; do
  ITERATION=$((ITERATION + 1))
  echo "Starting iteration $ITERATION"

  if [ $((ITERATION % 2)) -eq 0 ]; then
    CONFIG=/go_attack/configs/active-experiment.cfg
  else
    CONFIG=/go_attack/configs/iterated-training/alternate-experiment.cfg
  fi
  /go_attack/kubernetes/victimplay.sh --config "$CONFIG" "$WARMSTART_FLAG" \
    "$RUN_NAME"/iteration-"$ITERATION" "$VOLUME_NAME" &
  VICTIMPLAY_PID=$!

  ITERATION_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/iteration-"$ITERATION"
  while ! is_curriculum_complete $ITERATION_DIR; do
    assert_process_has_not_errored "$VICTIMPLAY_PID"
    sleep 10
  done
  echo "Finished iteration $ITERATION"
  echo "TT DEBUGGING: jobs before " $(jobs -p)
  kill $(jobs -p)
  echo "TT DEBUGGING: jobs after " $(jobs -p)
  # All iterations besides the first are warmstarted with the victim of the
  # previous iteration.
  WARMSTART_FLAG="--warmstart"
done
