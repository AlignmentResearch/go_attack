#!/bin/bash -eu

source "$(dirname "$0")"/common.sh

RUN_NAME="$1"
VOLUME_NAME="$2"
CURRICULUM_FILE="$3"
ALTERNATE_CURRICULUM_FILE="$4"

RUN_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/

INPUT_MODELS_DIR=/"$VOLUME_NAME"/victims
ITERATION_CURRICULUM_FILE="$CURRICULUM_FILE"
ITERATION=-1
while true; do
  ITERATION=$((ITERATION + 1))
  echo "Starting iteration $ITERATION"
  ITERATION_DIR="$RUN_DIR"/iteration-"$ITERATION"
  # Skip completed iterations (this may occur if the curriculum process is relaunched)
  if is_curriculum_complete "$ITERATION_DIR"; then
    continue
  fi

  run_until_curriculum_complete "$ITERATION_DIR" \
    /go_attack/kubernetes/curriculum.sh --input-models-dir "$INPUT_MODELS_DIR" \
    "$RUN_NAME"/iteration-"$ITERATION" "$VOLUME_NAME" \
    "$ITERATION_CURRICULUM_FILE"
  echo "Finished iteration $ITERATION"

  # For the next iteration, we set INPUT_MODELS_DIR and the curriculum to point
  # to the latest model trained in this iteration.
  # shellcheck disable=SC2012
  LATEST_MODEL=$(ls -v "$ITERATION_DIR"/models | tail --lines 1)
  INPUT_MODELS_DIR="$ITERATION_DIR"/models/"$LATEST_MODEL"

  NEXT_ITERATION_DIR="$RUN_DIR"/iteration-$((ITERATION + 1))
  mkdir --parents "$NEXT_ITERATION_DIR"/selfplay
  ITERATION_CURRICULUM_FILE="$NEXT_ITERATION_DIR"/selfplay/curriculum.json
  if [ $((ITERATION % 2)) -eq 0 ]; then
    BASE_CURRICULUM_FILE="$ALTERNATE_CURRICULUM_FILE"
  else
    BASE_CURRICULUM_FILE="$CURRICULUM_FILE"
  fi
  sed 's/"name": ".*",/"name": "model.bin.gz",/g' \
    "$BASE_CURRICULUM_FILE" > "$ITERATION_CURRICULUM_FILE"
done
