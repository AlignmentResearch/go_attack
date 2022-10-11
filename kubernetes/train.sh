#!/bin/bash -e
cd /engines/KataGo-custom/python
BASE_DIR="$1"
INITIAL_WEIGHTS_DIR="$2"

if [ -z "$INITIAL_WEIGHT_DIR" ]; then
    echo "No initial weights specified, using random weights"
else
    echo "Using initial weights: $INITIAL_WEIGHT_DIR"
    mkdir -p "$BASE_DIR"/train/t0
    cp -r "$INITIAL_WEIGHTS_DIR"/saved_model/model.config.json "$BASE_DIR"/train/t0/model.config.json
    cp -r "$INITIAL_WEIGHTS_DIR"/saved_model/variables "$BASE_DIR"/train/t0/initial_weights
fi

train_cmd=(
    ./selfplay/train.sh
    "$BASE_DIR"
    t0          # Name to prefix models with, specific to this training daemon
    b15c192     # Network size (if no initial weights specified)
    256         # Batch size
    main        # EXPORTMODE
    -disable-vtimeloss
    -lr-scale 1.0
    -max-train-bucket-per-new-data 4
)
"${train_cmd[@]}" # run command from array (https://stackoverflow.com/a/27196266/1337463)
