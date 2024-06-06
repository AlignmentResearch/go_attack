#!/bin/bash -e

MODEL_KIND=b6c96
COPY_INITIAL_MODEL=1
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149).
# Flags must be specified before positional arguments.
while [ -n "${1-}" ]; do
  case $1 in
    # Whether to copy model for warmstarting when --initial-weights is
    # specified. Usually we do want to copy the model, but for predictor
    # training, this flag should be used since the curriculum script will handle
    # copying the victim models for the predictor.
    --no-copy-initial-model) COPY_INITIAL_MODEL=0; ;;
    # Path to directory of TF weights for warmstarting.
    # For an official KataGo model, download the TF weights from
    # https://katagotraining.org/networks/, unzip them, and pass in the path to
    # the unzipped directory.
    # For one of your own training runs, pass in <path to your
    # training run>/models/<name of your model (something like t0-sNNN-dMMM)>.
    # Besides the TF weights, the C++ model needs to either also be in the
    # directory or to be in VOLUME_NAME/victims.
    --initial-weights) INITIAL_WEIGHTS=$2; shift ;;
    --model-kind) MODEL_KIND=$2; shift ;;
    --use-pytorch) USE_PYTORCH=1; ;;
    -*) echo "Unknown parameter passed: $1"; exit 1 ;;
    *) break ;;
  esac
  shift
done

RUN_NAME="$1"
VOLUME_NAME="$2"
LR_SCALE="$3"
shift
shift
shift

if [ -n "${USE_PYTORCH:-}" ]; then
  cd /engines/KataGo-custom/python
else
  cd /engines/KataGo-tensorflow/python
fi

EXPERIMENT_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"
if [ -z "$INITIAL_WEIGHTS" ]; then
    echo "No initial weights specified, using random weights"
elif [ -n "${USE_PYTORCH:-}" ]; then # handle PyTorch initial weights
    # For PyTorch, we expect INITIAL_WEIGHTS to contain `model.ckpt` for the
    # train code to initialize from and an exported model `model.bin.gz` or
    # `model.pt` for the C++ code to use.

    PYTORCH_CHECKPOINT="$INITIAL_WEIGHTS/model.ckpt"

    if [ "$COPY_INITIAL_MODEL" -eq "1" ] &&
       [ ! -f "$EXPERIMENT_DIR"/done-copying-warmstart-model ]; then
        TARGET_DIR="$EXPERIMENT_DIR"/models/t0-s0-d0
        mkdir --parents "$TARGET_DIR"

        if [ -f "$INITIAL_WEIGHTS/model.bin.gz" ]; then
            cp "$INITIAL_WEIGHTS/model.bin.gz" "$TARGET_DIR"/model.bin.gz
        elif [ -f "$INITIAL_WEIGHTS/model.pt" ]; then
            cp "$INITIAL_WEIGHTS/model.pt" "$TARGET_DIR"/model.pt
        else
            echo "Error: no exported model was found at $INITIAL_WEIGHTS."
            exit 1
        fi
        touch "$EXPERIMENT_DIR"/done-copying-warmstart-model
    fi
else # handle TensorFlow initial weights
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

    if [ "$COPY_INITIAL_MODEL" -eq "1" ] &&
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
      mkdir --parents "$TARGET_DIR"/saved_model
      cp "$INITIAL_MODEL" "$TARGET_DIR"/model."$MODEL_EXTENSION"
      # Copying the saved_model files isn't strictly necessary, but we copy them
      # in case we want to warmstart from this t0-s0-d0/ in a different run.
      cp "$INITIAL_WEIGHTS"/saved_model/model.config.json "$TARGET_DIR"/saved_model
      cp -r "$INITIAL_WEIGHTS"/saved_model/variables "$TARGET_DIR"/saved_model
      touch "$EXPERIMENT_DIR"/done-copying-warmstart-model
    fi
fi

# Only add the PyTorch-only flag -initial-checkpoint if we're warmstarting
# with PyTorch.
./selfplay/train.sh "$EXPERIMENT_DIR" t0 "$MODEL_KIND" 256 main \
  -disable-vtimeloss \
  -lr-scale "$LR_SCALE" \
  -max-train-bucket-per-new-data 4 \
  ${PYTORCH_CHECKPOINT:+"-initial-checkpoint" "$PYTORCH_CHECKPOINT"} \
  "$@"
