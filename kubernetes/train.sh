#!/bin/bash -eu
cd /engines/KataGo-custom/python

# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149).
# Flags must be specified before positional arguments.
while [ -n "${1-}" ]; do
  case $1 in
    # Path to model for warmstarting. If this flag is used,
    # --initial-weights flag should be specified as well.
    # For predictor training, this flag should not be specified since the
    # curriculum script will handle copying the victim models for the predictor.
    --initial-model) INITIAL_MODEL=$2; shift ;;
    # Path to directory of TF weights for warmstarting.
    --initial-weights) INITIAL_WEIGHTS=$2; shift ;;
    -*) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
    *) break ;;
  esac
  shift
done

RUN_NAME="$1"
VOLUME_NAME="$2"
LR_SCALE="$3"

EXPERIMENT_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"
if [ -z "${INITIAL_WEIGHTS:-}" ]; then
  if [ -n "${INITIAL_MODEL:-}" ]; then
    echo "Error: --initial-weights must be specified if --initial-model is"\
         "specified."
    exit 1
  fi
  echo "No initial weights specified, using random weights"
  MODEL_KIND=b6c96
else
  echo "Using initial weights: $INITIAL_WEIGHTS"
  # shellcheck disable=SC2001
  MODEL_KIND=$(echo "$INITIAL_WEIGHTS" | sed "s/.*\(b[0-9]\+c[0-9]\+\).*/\1/")

  if [ ! -d "$INITIAL_WEIGHTS" ]; then
    echo "Error: initial weights do not exist: $INITIAL_WEIGHTS"
    exit 1
  mkdir -p "$EXPERIMENT_DIR"/train/t0
  cp "$INITIAL_WEIGHTS"/saved_model/model.config.json "$EXPERIMENT_DIR"/train/t0/model.config.json
  cp -r "$INITIAL_WEIGHTS"/saved_model/variables "$EXPERIMENT_DIR"/train/t0/initial_weights

  if [ -n "${INITIAL_MODEL:-}" ]; then
    echo "Using initial model: $INITIAL_MODEL"
    if [ ! -f "$INITIAL_MODEL" ]; then
      echo "Error: initial model does not exist: $INITIAL_MODEL"
      exit 1
    fi
    if [ ! -f "$EXPERIMENT_DIR"/done-copying-warmstart-model ]; then
      mkdir -p "$EXPERIMENT_DIR"/models/t0-s0-d0
      cp "$INITIAL_MODEL" "$EXPERIMENT_DIR"/models/t0-s0-d0/
      touch "$EXPERIMENT_DIR"/done-copying-warmstart-model
    fi
  fi
fi

echo "Model kind: $MODEL_KIND"
./selfplay/train.sh "$EXPERIMENT_DIR" t0 "$MODEL_KIND" 256 main -disable-vtimeloss -lr-scale "$LR_SCALE" -max-train-bucket-per-new-data 4
