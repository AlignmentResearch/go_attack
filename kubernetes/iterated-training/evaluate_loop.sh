#!/bin/bash -eu
source "$(dirname "$0")"/common.sh

RUN_NAME="$1"
VOLUME_NAME="$2"

ITERATION=-1
while true; do
  ITERATION=$((ITERATION + 1))
  echo "Starting iteration $ITERATION"
  ITERATION_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/iteration-"$ITERATION"
  /engines/KataGo-custom/cpp/evaluate_loop.sh \
    "$ITERATION_DIR" "$ITERATION_DIR"/eval &
  EVALUATE_PID=$1

  while ! is_curriculum_complete "$ITERATION_DIR"; do
    assert_process_has_not_errored "$EVALUATE_PID"
    sleep 10
  done
  echo "Finished iteration $ITERATION"
  echo "TT DEBUGGING: jobs before $(jobs -p)"
  # shellcheck disable=SC2046
  kill $(jobs -p)
  echo "TT DEBUGGING: jobs after $(jobs -p)"
done
