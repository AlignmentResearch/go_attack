#!/bin/bash -e
cd /engines/KataGo-custom/python
RUN_NAME="$1"
VOLUME_NAME="$2"
EXPERIMENT_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"

INITIAL_WEIGHTS="b6c96-s175395328-d26788732" # cp63
INITIAL_MODEL="kata1-b6c96-s175395328-d26788732.txt.gz"

# INITIAL_WEIGHTS="kata1-b40c256-s11840935168-d2898845681" # cp505
# INITIAL_MODEL="kata1-b40c256-s11840935168-d2898845681.bin.gz"

if [ -z "$INITIAL_WEIGHTS" ]; then
    echo "No initial weights specified, using random weights"
else
    echo "Using initial weights: $INITIAL_WEIGHTS"

    INITIAL_WEIGHTS_DIR=/"$VOLUME_NAME"/victim-weights/"$INITIAL_WEIGHTS"/
    if [ ! -d $INITIAL_WEIGHTS_DIR ]; then
      echo "Initial weights do not exist: $INITIAL_WEIGHTS_DIR"
      exit 1
    fi
    mkdir -p "$EXPERIMENT_DIR"/train/t0
    cp "$INITIAL_WEIGHTS_DIR"/saved_model/model.config.json "$EXPERIMENT_DIR"/train/t0/model.config.json
    cp -r "$INITIAL_WEIGHTS_DIR"/saved_model/variables "$EXPERIMENT_DIR"/train/t0/initial_weights
fi

if [ -n "$INITIAL_MODEL" ] && [ ! -f "$EXPERIMENT_DIR"/done-copying-initial-model ]; then
    echo "Using initial model: $INITIAL_MODEL"
    INITIAL_MODEL=/"$VOLUME_NAME"/victims/$INITIAL_MODEL
    if [ ! -f $INITIAL_MODEL ]; then
      echo "Initial model does not exist: $INITIAL_MODEL"
      exit 1
    fi
    MODEL_EXTENSION=${INITIAL_MODEL: -6} # bin.gz or txt.gz
    mkdir -p "$EXPERIMENT_DIR"/models/t0-s0-d0
    cp "$INITIAL_MODEL" "$EXPERIMENT_DIR"/models/t0-s0-d0/model."$MODEL_EXTENSION"
    touch "$EXPERIMENT_DIR"/done-copying-initial-model
fi

./selfplay/train.sh    /"$VOLUME_NAME"/victimplay/"$RUN_NAME"    t0    b6c96    256    main    -disable-vtimeloss    -lr-scale 1.0   -max-train-bucket-per-new-data 4
