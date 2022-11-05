#!/bin/bash -e
# Logs the git commit (assumed to be saved in the GIT_COMMIT environment
# variable) used for an experiment.

OUTPUT_DIR=$1

mkdir -p "$OUTPUT_DIR"
COMMIT_FILE="$OUTPUT_DIR"/commit
GIT_COMMIT=${GIT_COMMIT:-no_commit_found}

if [ -f "$COMMIT_FILE" ]; then
  # COMMIT_FILE already exists, but we may still want to log the commit if the
  # commit has changed due to restarting a job.
  LATEST_COMMIT=$(tail -n 1 "$COMMIT_FILE" | awk '{print $2}')
  if [ "$LATEST_COMMIT" != "$GIT_COMMIT" ]; then
    echo "$(date +%Y%m%d-%H%M%S) $GIT_COMMIT" >> "$COMMIT_FILE"
  fi
else
  echo "$(date +%Y%m%d-%H%M%S) $GIT_COMMIT" >> "$COMMIT_FILE"
fi
