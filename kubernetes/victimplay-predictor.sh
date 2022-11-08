#!/bin/sh
RUN_NAME="$1"
VOLUME_NAME="$2"
mkdir -p /"$VOLUME_NAME"/victimplay/"$RUN_NAME"
/engines/KataGo-custom/cpp/katago victimplay \
    -output-dir /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/selfplay/ \
    -models-dir /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/models/ \
    -nn-predictor-path /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/predictor/models \
    -nn-victim-path /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/victims/ \
    -config /go_attack/configs/active-experiment.cfg \
    -config /go_attack/configs/compute/1gpu.cfg \
    -victim-output-dir /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/predictor/selfplay
