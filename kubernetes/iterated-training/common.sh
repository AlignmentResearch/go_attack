#!/bin/sh -eu
# Common functions shared among iterated training scripts.

# Checks if the curriculum has finished for the run in directory $1. If it has
# finished, the function exits with exit code 0, otherwise it exits with a
# non-zero exit code.
is_curriculum_complete() {
  CURRICULUM_LOG_DIR="$1"/selfplay
  if [ ! -d "$CURRICULUM_LOG_DIR" ]; then
    false
    return
  fi
  LATEST_CURRICULUM_LOG=$(ls -v $CURRICULUM_LOG_DIR | grep ^curriculum-.*\.log | tail --lines 1)
  LATEST_CURRICULUM_LOG="$CURRICULUM_LOG_DIR"/"$LATEST_CURRICULUM_LOG"
  LAST_LOG_LINE=$(tail --lines 1 $LATEST_CURRICULUM_LOG)
  [[ $LAST_LOG_LINE == "Curriculum is done"* ]]
  return
}
