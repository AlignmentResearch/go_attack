#!/bin/sh
BASE_DIR="$1"
mkdir -p "$BASE_DIR"
/engines/KataGo-custom/cpp/katago victimplay \
    -output-dir "$BASE_DIR"/selfplay \
    -models-dir "$BASE_DIR"/models \
    -nn-victim-path "$BASE_DIR"/victims \
    -victim-output-dir "$BASE_DIR"/predictor/selfplay \
    -nn-predictor-path "$BASE_DIR"/predictor/models \
    -config /go_attack/configs/active-experiment.cfg \
    -config /go_attack/configs/compute/1gpu.cfg
