#!/bin/sh
RUN_NAME="$1"
VOLUME_NAME="$2"
CURRICULUM_FILE="$3"
python /engines/KataGo-custom/python/curriculum.py \
    -selfplay-dir=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/selfplay/ \
    -input-models-dir=/"$VOLUME_NAME"/victims \
    -output-models-dir=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/victims \
    -config-json-file="${CURRICULUM_FILE:-/go_attack/configs/curriculum.json}"

sleep infinity
