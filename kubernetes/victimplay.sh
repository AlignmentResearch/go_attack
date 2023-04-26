#!/bin/sh
RUN_NAME="$1"
VOLUME_NAME="$2"
USE_WARMSTART="$3"

while [ "$USE_WARMSTART" -ne 0 ] &&
      [ ! -f /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/done-copying-warmstart-model ]; do
  echo "Waiting for train.sh to copy initial warmstart model"
  sleep 30;
done

mkdir -p /"$VOLUME_NAME"/victimplay/"$RUN_NAME"
/engines/KataGo-raw/cpp/katago selfplay \
    -output-dir /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/selfplay/ \
    -models-dir /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/models/ \
    -config /go_attack/engines/KataGo-raw/cpp/configs/training/selfplay1.cfg
