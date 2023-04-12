#!/bin/bash -eu
# Common functions shared among iterated training scripts.

# Returns exit code 0 if the process with PID $1 is still running, otherwise
# returns a non-zero exit code.
is_process_running() {
  local PID=$1
  ps -p "$PID" > /dev/null
  return
}

# Returns exit code 0 if the process with PID $1 has exited with an error.
# Returns exit code 1 if the process is still running or exited without an
# error.
has_process_errored() {
  local PID=$1
  if is_process_running "$PID"; then
    return 1
  fi
  # shellcheck disable=SC2215
  ! wait "$PID"
  return
}

# Checks if the curriculum has finished for the run in directory $1. If it has
# finished, the function returns exit code 0, otherwise it returns a non-zero
# exit code.
is_curriculum_done() {
  local CURRICULUM_LOG_DIR="$1"/selfplay
  if [ ! -d "$CURRICULUM_LOG_DIR" ]; then
    return 1
  fi
  local CURRICULUM_LOGS
  # shellcheck disable=SC2010
  CURRICULUM_LOGS=$(ls -v "$CURRICULUM_LOG_DIR" | grep "^curriculum-.*\.log")
  if [ -z "$CURRICULUM_LOGS" ]; then
    return 1
  fi
  local LATEST_CURRICULUM_LOG
  LATEST_CURRICULUM_LOG=$(echo "$CURRICULUM_LOGS" | tail --lines 1)
  LATEST_CURRICULUM_LOG="$CURRICULUM_LOG_DIR"/"$LATEST_CURRICULUM_LOG"
  local LAST_LOG_LINE
  LAST_LOG_LINE=$(tail --lines 1 "$LATEST_CURRICULUM_LOG")
  [[ $LAST_LOG_LINE == "Curriculum finished"* ]]
  return
}

# Runs a command in the background until the victimplay curriculum finishes.
# $1 is the output directory for the victimplay run, and the remaining arguments
# are the command to run.
# Returns exit code 1 if the command errors.
run_until_curriculum_done() {
  local RUN_DIR=$1
  shift

  if is_curriculum_done "$RUN_DIR"; then
    return 0
  fi

  # To make sure we also kill any child processes when we run the command, we
  # use setsid to give the command its own process group. Then we can kill that
  # process group to kill the command along with all its child processes.
  setsid "$@" &
  local COMMAND_PID=$!

  while ! is_curriculum_done "$RUN_DIR"; do
    if has_process_errored "$COMMAND_PID"; then
      echo "Error: process $COMMAND_PID exited with an error."
      return 1
    fi
    sleep 15
  done
  kill -- -"$COMMAND_PID" || true
}
