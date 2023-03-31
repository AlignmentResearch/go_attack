#!/bin/sh -eu
RUN_NAME="$1"
VOLUME_NAME="$2"

source $(dirname $0)/common.sh

ITERATION=-1
while true; do
  ITERATION=$((ITERATION + 1))
  echo "Starting iteration $ITERATION"

  USE_GATING=0
  /go_attack/kubernetes/shuffle-and-export.sh \
    "$RUN_NAME"-"$ITERATION" "$RUN_NAME"/iteration-"$ITERATION" \
    "$VOLUME_NAME" "$USE_GATING"

  ITERATION_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/iteration-"$ITERATION"
  while ! is_curriculum_complete $ITERATION_DIR; do
    sleep 10
  done
  echo "Finished iteration $ITERATION"
  echo "TT DEBUGGING: jobs before " $(jobs -p)
  # Kill background shuffle and export processes
  kill $(jobs -p)
  echo "TT DEBUGGING: jobs after " $(jobs -p)
done
