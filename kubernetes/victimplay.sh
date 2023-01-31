#!/bin/sh
RUN_NAME="$1"
VOLUME_NAME="$2"

while [ ! -f /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/done-copying-initial-model ]; do
  # dumb hack. maybe this script should do the copying instead of train.sh, i
  # just don't want to think about how to deal with this when there are multiple
  # replicas running this script
  echo "Waiting for train.sh to copy initial model"
  sleep 30;
done

mkdir -p /"$VOLUME_NAME"/victimplay/"$RUN_NAME"
/engines/KataGo-custom/cpp/katago selfplay \
    -output-dir /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/selfplay/ \
    -models-dir /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/models/ \
    -nn-victim-path /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/victims/ \
    -config /go_attack/configs/active-experiment.cfg \
    -config /go_attack/configs/compute/1gpu.cfg
