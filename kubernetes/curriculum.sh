#!/bin/sh
RUN_NAME="$1"
VOLUME_NAME="$2"

# not related to curriculum but we want some process to log this
/go_attack/kubernetes/log-git-commit.sh /"$VOLUME_NAME"/victimplay/"$RUN_NAME"

python /engines/KataGo-custom/python/curriculum.py \
    -selfplay-dir=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/selfplay/ \
    -input-models-dir=/"$VOLUME_NAME"/victims \
    -output-models-dir=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/victims \
    -config-json-file=/go_attack/configs/curriculum.json

sleep infinity
