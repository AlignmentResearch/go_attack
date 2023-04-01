#!/bin/bash -eu

# The command line flags have same meaning as in from kubernetes/train.sh.
WARMSTART_FLAGS=
while [ -n "${1-}" ]; do
  case $1 in
    --copy-initial-model) WARMSTART_FLAGS+=" $1" ;;
    --initial-weights) WARMSTART_FLAGS+=" $1 $2"; shift ;;
    -*) echo "Unknown parameter passed: $1"; exit 1 ;;
    *) break ;;
  esac
  shift
done

RUN_NAME="$1"
VOLUME_NAME="$2"
LR_SCALE="$3"
# --initial-weights specifies the initial adversary weights, whereas this
# required argument specifies the initial victim weights (needed for
# warmstarting the second iteration of iterated training).
INITIAL_VICTIM_WEIGHTS=$4

RUN_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/
source $(dirname $0)/common.sh

ITERATION=-1
while true; do
  ITERATION=$((ITERATION + 1))
  echo "Starting iteration $ITERATION"

  if [ "$ITERATION" -eq 1 ]; then
    WARMSTART_FLAGS="--copy-initial-model --initial-weights $INITIAL_VICTIM_WEIGHTS"
  elif [ "$ITERATION" -gt 1 ]; then
    # Warmstart from the victim of the previous iteration, which is the
    # latest trained adversary from two iterations ago.
    WARMSTART_ITERATION_DIR="$RUN_DIR"/iteration-$((ITERATION - 2))
    LATEST_MODEL=$(ls -v "$WARMSTART_ITERATION_DIR"/models | tail --lines 1)
    WARMSTART_FLAGS="--copy-initial-model --initial-weights $WARMSTART_ITERATION_DIR/models/$LATEST_MODEL"
  fi

  /go_attack/kubernetes/train.sh \
    $WARMSTART_FLAGS $RUN_NAME/iteration-"$ITERATION" \
    "$VOLUME_NAME" "$LR_SCALE" &
  TRAIN_PID=$!

  ITERATION_DIR=/"$RUN_DIR"/iteration-"$ITERATION"
  while ! is_curriculum_complete $ITERATION_DIR; do
    assert_process_has_not_errored "$TRAIN_PID"
    sleep 10
  done
  echo "Finished iteration $ITERATION"
  echo "TT DEBUGGING: jobs before " $(jobs -p)
  kill $(jobs -p)
  echo "TT DEBUGGING: jobs after " $(jobs -p)
done
