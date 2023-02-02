#!/bin/sh
RUN_NAME="$1"
VOLUME_NAME="$2"

while [ ! -f /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/done-copying-initial-model ]; do
  echo "Waiting for train.sh to copy initial model"
  sleep 30;
done

mkdir -p /"$VOLUME_NAME"/victimplay/"$RUN_NAME"
/engines/KataGo-custom/cpp/katago victimplay \
    -output-dir /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/selfplay/ \
    -models-dir /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/models/ \
    -nn-victim-path /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/victims/ \
    -config /go_attack/configs/active-experiment.cfg \
    -config /go_attack/configs/compute/1gpu.cfg
