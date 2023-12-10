#!/bin/bash -e
cd /engines/KataGo-custom/python

# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149).
# Flags must be specified before positional arguments.
while [ -n "${1-}" ]; do
  case $1 in
    # Whether to copy model for warmstarting. If this flag is used,
    # --initial-weights flag should be specified as well.
    # For predictor training, this flag should not be specified since the
    # curriculum script will handle copying the victim models for the predictor.
    --copy-initial-model) COPY_INITIAL_MODEL=1; ;;
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
if [ ! -e "$EXPERIMENT_DIR/selfplay/prev-selfplay" ]; then
  mkdir --parents "$EXPERIMENT_DIR/selfplay/prev-selfplay"
  ln -s /shared/victimplay/ttseng-cp505-h6-20231203/iteration-0/selfplay/prev-selfplay "$EXPERIMENT_DIR"/selfplay/prev-selfplay/prev-selfplay

  ln -s /shared/victimplay/ttseng-cp505-h6-20231203/iteration-0/selfplay/prev-selfplay/t0-s0-d0 "$EXPERIMENT_DIR"/selfplay/prev-selfplay
  ln -s /shared/victimplay/ttseng-cp505-h6-20231203/iteration-0/selfplay/t0-s998400-d72492718 "$EXPERIMENT_DIR"/selfplay/prev-selfplay
  ln -s /shared/victimplay/ttseng-cp505-h6-20231203/iteration-0/selfplay/t0-s2138624-d72822181 "$EXPERIMENT_DIR"/selfplay/prev-selfplay
  ln -s /shared/victimplay/ttseng-cp505-h6-20231203/iteration-0/selfplay/t0-s3206912-d73318303 "$EXPERIMENT_DIR"/selfplay/prev-selfplay
  ln -s /shared/victimplay/ttseng-cp505-h6-20231203/iteration-0/selfplay/t0-s4276224-d73569187 "$EXPERIMENT_DIR"/selfplay/prev-selfplay
  ln -s /shared/victimplay/ttseng-cp505-h6-20231203/iteration-0/selfplay/t0-s5273344-d73956377 "$EXPERIMENT_DIR"/selfplay/prev-selfplay
  ln -s /shared/victimplay/ttseng-cp505-h6-20231203/iteration-0/selfplay/t0-s6200832-d74076955 "$EXPERIMENT_DIR"/selfplay/prev-selfplay
  ln -s /shared/victimplay/ttseng-cp505-h6-20231203/iteration-0/selfplay/t0-s7269632-d74429680 "$EXPERIMENT_DIR"/selfplay/prev-selfplay
  ln -s /shared/victimplay/ttseng-cp505-h6-20231203/iteration-0/selfplay/t0-s8268288-d74685063 "$EXPERIMENT_DIR"/selfplay/prev-selfplay
  ln -s /shared/victimplay/ttseng-cp505-h6-20231203/iteration-0/selfplay/t0-s9194752-d74981633 "$EXPERIMENT_DIR"/selfplay/prev-selfplay
  ln -s /shared/victimplay/ttseng-cp505-h6-20231203/iteration-0/selfplay/t0-s10123520-d75284816 "$EXPERIMENT_DIR"/selfplay/prev-selfplay
  ln -s /shared/victimplay/ttseng-cp505-h6-20231203/iteration-0/selfplay/t0-s11051008-d75604814 "$EXPERIMENT_DIR"/selfplay/prev-selfplay
  ln -s /shared/victimplay/ttseng-cp505-h6-20231203/iteration-0/selfplay/t0-s11906304-d75871082 "$EXPERIMENT_DIR"/selfplay/prev-selfplay
fi

if [ -z "$INITIAL_WEIGHTS" ]; then
    echo "No initial weights specified, using random weights"
    MODEL_KIND=b6c96
else
    echo "Using initial weights: $INITIAL_WEIGHTS"
    # The train script will use the model kind specified by the warmstarted
    # model's config. MODEL_KIND is ignored.
    MODEL_KIND="unused"

    if [ ! -d "$INITIAL_WEIGHTS" ]; then
        echo "Error: initial weights do not exist: $INITIAL_WEIGHTS"
        exit 1
    fi
    mkdir -p "$EXPERIMENT_DIR"/train/t0/initial_weights
    cp "$INITIAL_WEIGHTS"/saved_model/model.config.json "$EXPERIMENT_DIR"/train/t0/model.config.json
    cp -r "$INITIAL_WEIGHTS"/saved_model/variables/* "$EXPERIMENT_DIR"/train/t0/initial_weights

    if [ -n "${COPY_INITIAL_MODEL:-}" ] &&
       [ ! -f "$EXPERIMENT_DIR"/done-copying-warmstart-model ]; then
      INITIAL_MODEL=""
      ADV_MODEL="$INITIAL_WEIGHTS/model.bin.gz"
      if [ -f "$ADV_MODEL" ]; then
          # If the warmstart model is an adversary, then we expect model.bin.gz to
          # exist in $INITIAL_WEIGHTS.
          INITIAL_MODEL="$ADV_MODEL"
      else
          # Warmstart model is a victim, so we search $VICTIM_MODELS_DIR for the
          # victim model.
          VICTIM_MODELS_DIR=/"$VOLUME_NAME"/victims
          INITIAL_WEIGHTS_BASENAME=$(basename "$INITIAL_WEIGHTS")
          POSSIBLE_MODEL_NAMES=(\
              "kata1-$INITIAL_WEIGHTS_BASENAME.txt.gz"
              "kata1-$INITIAL_WEIGHTS_BASENAME.bin.gz"
              "$INITIAL_WEIGHTS_BASENAME.bin.gz"
          )
          for POSSIBLE_NAME in "${POSSIBLE_MODEL_NAMES[@]}"; do
              POSSIBLE_MODEL="$VICTIM_MODELS_DIR/$POSSIBLE_NAME"
              if [ -f "$POSSIBLE_MODEL" ]; then
                  INITIAL_MODEL="$POSSIBLE_MODEL"
                  break
              fi
          done
      fi
      if [ -z "$INITIAL_MODEL" ]; then
          echo "Error: initial weights exist at $INITIAL_WEIGHTS_DIR, but no"\
               "matching model was found."
          exit 1
      fi
      echo "Using initial model: $INITIAL_MODEL"
      MODEL_EXTENSION=${INITIAL_MODEL: -6} # bin.gz or txt.gz
      TARGET_DIR="$EXPERIMENT_DIR"/models/t0-s0-d0
      mkdir -p "$TARGET_DIR"/saved_model
      cp "$INITIAL_MODEL" "$TARGET_DIR"/model."$MODEL_EXTENSION"
      # Copying the saved_model files isn't strictly necessary, but we copy them
      # in case we want to warmstart from this t0-s0-d0/ in a different run.
      cp "$INITIAL_WEIGHTS"/saved_model/model.config.json "$TARGET_DIR"/saved_model
      cp -r "$INITIAL_WEIGHTS"/saved_model/variables "$TARGET_DIR"/saved_model
      touch "$EXPERIMENT_DIR"/done-copying-warmstart-model
    fi
fi

./selfplay/train.sh "$EXPERIMENT_DIR" t0 "$MODEL_KIND" 256 main -disable-vtimeloss -lr-scale "$LR_SCALE" -max-train-bucket-per-new-data 4
