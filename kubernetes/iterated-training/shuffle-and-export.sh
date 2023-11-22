#!/bin/bash -eu

source "$(dirname "$0")"/common.sh

RUN_NAME="$1"
VOLUME_NAME="$2"

ITERATION=-1
while true; do
  ITERATION=$((ITERATION + 1))
  echo "Starting iteration $ITERATION"

  ITERATION_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/iteration-"$ITERATION"
  run_until_curriculum_done "$ITERATION_DIR" \
    /go_attack/kubernetes/shuffle-and-export.sh "$RUN_NAME"-"$ITERATION" \
    "$RUN_NAME"/iteration-"$ITERATION" "$VOLUME_NAME"
done
