#!/bin/bash -eu
RUN_NAME="$1"
VOLUME_NAME="$2"

source $(dirname $0)/common.sh

ITERATION=-1
while true; do
  ITERATION=$((ITERATION + 1))
  echo "Starting iteration $ITERATION"
  ITERATION_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/iteration-"$ITERATION"
  /engines/KataGo-custom/cpp/evaluate_loop.sh \
    "$ITERATION_DIR" "$ITERATION_DIR"/eval &

  while ! is_curriculum_complete $ITERATION_DIR; do
    sleep 10
  done
  echo "Finished iteration $ITERATION"
  echo "TT DEBUGGING: jobs before " $(jobs -p)
  kill $(jobs -p)
  echo "TT DEBUGGING: jobs after " $(jobs -p)
done
