#!/bin/bash
RUN_NAME="$1"
VOLUME_NAME="$2"

TRAINING_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"
mkdir -p "$TRAINING_DIR"

/engines/KataGo-custom/cpp/katago victimplaygatekeeper \
  -config /go_attack/configs/amcts/gatekeeper.cfg \
  -config /go_attack/configs/compute/1gpu.cfg \
  -accepted-models-dir "$TRAINING_DIR/models"  \
  -rejected-models-dir "$TRAINING_DIR/models_rejected" \
  -test-models-dir "$TRAINING_DIR/modelstobetested" \
  -victim-models-dir "$TRAINING_DIR/victims" \
  -sgf-output-dir "$TRAINING_DIR/gatekeeper_sgfs"  \
  -selfplay-dir "$TRAINING_DIR/selfplay"
