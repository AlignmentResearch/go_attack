#!/bin/bash -eu
# Common functions shared among iterated training scripts.

# Returns exit code 0 if the process with PID $1 is still running, otherwise
# returns a non-zero exit code.
is_process_running() {
  PID=$1
  ps -p "$PID" > /dev/null
  return
}

# Exits the script if the process with PID $1 has exited with an error. Returns
# exit code 0 if the process is still running or exited without an error.
assert_process_has_not_errored() {
  PID=$1
  if is_process_running "$PID"; then
    return 0
  fi
  if ! wait "$PID"; then
    echo "Error: process $PID exited with an error."
    exit 1
  fi
}

# Checks if the curriculum has finished for the run in directory $1. If it has
# finished, the function returns exit code 0, otherwise it returns a non-zero
# exit code.
is_curriculum_complete() {
  CURRICULUM_LOG_DIR="$1"/selfplay
  if [ ! -d "$CURRICULUM_LOG_DIR" ]; then
    false
    return
  fi
  # shellcheck disable=SC2010
  CURRICULUM_LOGS=$(ls -v "$CURRICULUM_LOG_DIR" | grep "^curriculum-.*\.log")
  if [ -z "$CURRICULUM_LOGS" ]; then
    false
    return
  fi
  LATEST_CURRICULUM_LOG=$(echo "$CURRICULUM_LOGS" | tail --lines 1)
  LATEST_CURRICULUM_LOG="$CURRICULUM_LOG_DIR"/"$LATEST_CURRICULUM_LOG"
  LAST_LOG_LINE=$(tail --lines 1 "$LATEST_CURRICULUM_LOG")
  [[ $LAST_LOG_LINE == "Curriculum finished"* ]]
  return
}

# Runs a command until the victimplay curriculum finishes.
# $1 is the output directory for the victimplay run, and the remaining arguments
# are the command to run.
run_until_curriculum_done() {
  RUN_DIR=$1
  shift
  COMMAND="$@"

  # To make sure we also kill any child processes when we run the command, we
  # use setsid to give the command its own process group. Then we can kill that
  # process group to kill the command along with all its child processes.
  setsid "$COMMAND" &
  COMMAND_PID=$1

  while ! is_curriculum_complete "$ITERATION_DIR"; do
    assert_process_has_not_errored "$VICTIMPLAY_PID"
    sleep 10
  done
  kill -- -"$COMMAND_PID"
}
