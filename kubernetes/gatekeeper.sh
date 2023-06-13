#!/bin/bash -eu
RUN_NAME="$1"
VOLUME_NAME="$2"

TRAINING_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"
mkdir -p "$TRAINING_DIR"

/engines/KataGo-custom/cpp/katago gatekeeper \
  -config /go_attack/engines/KataGo-raw/cpp/configs/training/gatekeeper1.cfg \
  -accepted-models-dir "$TRAINING_DIR/models"  \
  -rejected-models-dir "$TRAINING_DIR/rejectedmodels" \
  -test-models-dir "$TRAINING_DIR/modelstobetested" \
  -sgf-output-dir "$TRAINING_DIR/gatekeepersgf"  \
  -selfplay-dir "$TRAINING_DIR/selfplay"
