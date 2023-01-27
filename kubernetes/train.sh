#!/bin/bash -e
cd /engines/KataGo-custom/python
RUN_NAME="$1"
VOLUME_NAME="$2"
INITIAL_WEIGHTS="$3"

EXPERIMENT_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"
if [ -z "$INITIAL_WEIGHTS" ]; then
    echo "No initial weights specified, using random weights"
    MODEL_KIND=b6c96
else
    echo "Using initial weights: $INITIAL_WEIGHTS"
    MODEL_KIND=$(echo "$INITIAL_WEIGHTS" | sed "s/.*\(b[0-9]\+c[0-9]\+\).*/\1/")

    INITIAL_WEIGHTS_DIR=/"$VOLUME_NAME"/victim-weights/"$INITIAL_WEIGHTS"/
    if [ ! -d $INITIAL_WEIGHTS_DIR ]; then
        echo "Initial weights do not exist: $INITIAL_WEIGHTS_DIR"
        exit 1
    fi
    mkdir -p "$EXPERIMENT_DIR"/train/t0
    cp "$INITIAL_WEIGHTS_DIR"/saved_model/model.config.json "$EXPERIMENT_DIR"/train/t0/model.config.json
    cp -r "$INITIAL_WEIGHTS_DIR"/saved_model/variables "$EXPERIMENT_DIR"/train/t0/initial_weights

    if [ ! -f "$EXPERIMENT_DIR"/done-copying-warmstart-model ]; then
      FOUND_MODEL=0
      VICTIM_MODELS_DIR=/"$VOLUME_NAME"/victims
      POSSIBLE_MODEL_NAMES=(\
          "kata1-$INITIAL_WEIGHTS_DIR.txt.gz"
          "kata1-$INITIAL_WEIGHTS_DIR.bin.gz"
          "$INITIAL_WEIGHTS_DIR.bin.gz"
      )
      for POSSIBLE_NAME in ${POSSIBLE_MODEL_NAMES[@]}; do
          INITIAL_MODEL="$VICTIM_MODELS_DIR/$POSSIBLE_NAME"
          if [ -f "$MODEL" ]; then
              echo "Using initial model: $INITIAL_MODEL"
              FOUND_MODEL=1
          fi
          MODEL_EXTENSION=${INITIAL_MODEL: -6} # bin.gz or txt.gz
          mkdir -p "$EXPERIMENT_DIR"/models/t0-s0-d0
          cp "$INITIAL_MODEL" "$EXPERIMENT_DIR"/models/t0-s0-d0/model."$MODEL_EXTENSION"
          touch "$EXPERIMENT_DIR"/done-copying-warmstart-model
      done
      if [ $FOUND_MODEL -eq 0 ]; then
          echo "Did not find initial model $INITIAL_WEIGHTS_DIR"
          exit 1
      fi
    fi
fi

echo "Model kind: $MODEL_KIND"
./selfplay/train.sh    "$EXPERIMENT_DIR"    t0    "$MODEL_KIND"    256    main    -disable-vtimeloss    -lr-scale 1.0    -max-train-bucket-per-new-data 4
