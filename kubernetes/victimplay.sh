#!/bin/sh -e

CONFIG=/go_attack/configs/active-experiment.cfg
while [ -n "${1-}" ]; do
  case $1 in
    # Specifies the config to use.
    --config) CONFIG=$2; shift ;;
    # Specifies that this is a warmstart run.
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
    -nn-victim-path /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/victims/ \
    -config "$CONFIG" \
    -config /go_attack/configs/compute/1gpu.cfg
