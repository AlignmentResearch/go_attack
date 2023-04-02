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
    /engines/KataGo-custom/cpp/evaluate_loop.sh "$ITERATION_DIR" \
    "$ITERATION_DIR"/eval
done
