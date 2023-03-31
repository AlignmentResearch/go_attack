#!/bin/sh

while [ -n "${1-}" ]; do
  case $1 in
    --warmstart) USE_WARMSTART=1; ;;
    -*) echo "Unknown parameter passed: $1"; exit 1 ;;
    *) break ;;
  esac
  shift
done

RUN_NAME="$1"
VOLUME_NAME="$2"

while [ -n "${USE_WARMSTART:-}" ] &&
      [ ! -f /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/done-copying-warmstart-model ]; do
  echo "Waiting for train.sh to copy initial warmstart model"
  sleep 30;
done

mkdir -p /"$VOLUME_NAME"/victimplay/"$RUN_NAME"
/engines/KataGo-custom/cpp/katago victimplay \
    -output-dir /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/selfplay/ \
    -models-dir /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/models/ \
    -nn-predictor-path /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/predictor/models \
    -nn-victim-path /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/victims/ \
    -config /go_attack/configs/active-experiment.cfg \
    -config /go_attack/configs/compute/1gpu.cfg \
    -victim-output-dir /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/predictor/selfplay
