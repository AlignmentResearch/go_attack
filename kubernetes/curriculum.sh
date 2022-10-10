#!/bin/sh
BASE_DIR="$1"
MODEL_DIR="$2"
mkdir -p "$BASE_DIR"/selfplay
python /engines/KataGo-custom/python/curriculum.py \
    -selfplay-dir="$BASE_DIR"/selfplay \
    -input-models-dir="$MODEL_DIR" \
    -output-models-dir="$BASE_DIR"/victims \
    -config-json-file=/go_attack/configs/curriculum.json
