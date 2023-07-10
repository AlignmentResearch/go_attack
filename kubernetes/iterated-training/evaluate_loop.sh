#!/bin/bash -eu
source "$(dirname "$0")"/common.sh

RUN_NAME="$1"
VOLUME_NAME="$2"
ALTERNATE_ITERATION_FIRST="$3"

ITERATION=-1
while true; do
  ITERATION=$((ITERATION + 1))
  echo "Starting iteration $ITERATION"

  if [ $((ITERATION % 2)) -eq "$ALTERNATE_ITERATION_FIRST" ]; then
    CONFIG=/go_attack/configs/match-1gpu.cfg
  else
    CONFIG=/go_attack/configs/iterated-training/alternate-match-1gpu.cfg
  fi

  ITERATION_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/iteration-"$ITERATION"
  run_until_curriculum_done "$ITERATION_DIR" \
    /go_attack/kubernetes/evaluate_loop_custom.sh --config "$CONFIG" \
    "$ITERATION_DIR" "$ITERATION_DIR"/eval
done
