#!/bin/bash -eu
# Example script for symlinking pre-training data for ViT slowly so that each
# epoch of pre-training sees approximately one epoch's worth of newer data.
# This is run from `selfplay/prev-selfplay` of the experiment directory for the
# ViT to be pre-trained.

# This should be approximately how long each training epoch takes.
SLEEP_DURATION=1100

# Here we assume the previous ViT's experiment name is "vit-b4".
mkdir --parents b4
SRC_DIR=$(realpath ../../../vit-b4/selfplay)
DST_DIR=b4
SELFPLAY_MODELS=($(ls -v $SRC_DIR))
for MODEL in "${SELFPLAY_MODELS[@]}"; do
  SRC="$SRC_DIR/$MODEL"
  if [[ "$MODEL" =~ -s([0-9]+) ]]; then
    DST="$DST_DIR/$MODEL"
    STEP=${BASH_REMATCH[1]}

    # Optional: Here we choose to only copy b4's training data from 113 million steps
    # onwards, assuming that this still leaves enough data that we could afford to
    # throw away earlier lower quality data.
    # If you do this, you may want to append the `-add-to-window <number of omitted
    # data rows>` flag to the shuffler to increase the sliding window to the
    # size it would be if you did not omit the early training data.
    if [ "$STEP" -gt "112900000" ] && [ ! -e "$DST" ]; then
      echo "linking $SRC -> $DST"
      ln -s "$SRC" "$DST"
      sleep "$SLEEP_DURATION"
    fi
  fi
done
