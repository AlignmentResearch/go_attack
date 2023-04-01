#!/bin/bash -eu

source "$(dirname "$0")"/common.sh

RUN_NAME="$1"
VOLUME_NAME="$2"

ITERATION=-1
while true; do
  ITERATION=$((ITERATION + 1))
  echo "Starting iteration $ITERATION"

  USE_GATING=0
  /go_attack/kubernetes/shuffle-and-export.sh \
    "$RUN_NAME"-"$ITERATION" "$RUN_NAME"/iteration-"$ITERATION" \
    "$VOLUME_NAME" "$USE_GATING"

  ITERATION_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/iteration-"$ITERATION"
  while ! is_curriculum_complete "$ITERATION_DIR"; do
    sleep 10
  done
  echo "Finished iteration $ITERATION, killing processes $(jobs -p)"
  # Kill background shuffle and export processes
  # shellcheck disable=SC2046
  kill $(jobs -p)
done
