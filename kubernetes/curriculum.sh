#!/bin/sh
python /engines/KataGo-custom/python/curriculum.py \
    -selfplay-dir=/shared/victimplay/"$1"/selfplay/ \
    -input-models-dir=/shared/victims \
    -output-models-dir=/shared/victimplay/"$1"/victims \
    -config-json-file=/shared/configs/curriculum-cp37.json