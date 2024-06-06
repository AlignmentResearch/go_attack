#!/bin/bash -eu

CONFIG=/go_attack/configs/active-experiment.cfg
while [ -n "${1-}" ]; do
  case $1 in
    # Specifies the config to use.
    --config) CONFIG=$2; shift ;;
    # Use self-play instead of victim-play. (The training run is still stored in
    # the VOLUME_NAME/victimplay/ directory since other kubernetes/ scripts
    # assume that runs are stored there.)
    --selfplay) USE_SELFPLAY=1 ;;
    # Specifies that this is a warmstart run.
    --warmstart) USE_WARMSTART=1; ;;
    -*) echo "Unknown parameter passed: $1"; exit 1 ;;
    *) break ;;
  esac
  shift
done

RUN_NAME="$1"
VOLUME_NAME="$2"
shift
shift

while [ -n "${USE_WARMSTART:-}" ] &&
      [ ! -f /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/done-copying-warmstart-model ]; do
  echo "Waiting for train.sh to copy initial warmstart model"
  sleep 30;
done

mkdir -p /"$VOLUME_NAME"/victimplay/"$RUN_NAME"
KATAGO_BIN=/engines/KataGo-custom/cpp/katago
FLAGS=(
  "-output-dir" "/$VOLUME_NAME/victimplay/$RUN_NAME/selfplay/"
  "-models-dir" "/$VOLUME_NAME/victimplay/$RUN_NAME/models/"
  "-config" "$CONFIG"
  "-config" "/go_attack/configs/compute/1gpu.cfg"
)
if [ -n "${USE_SELFPLAY:-}" ]; then
  $KATAGO_BIN selfplay "${FLAGS[@]}" "$@"
else
  $KATAGO_BIN victimplay "${FLAGS[@]}" \
    -nn-victim-path /"$VOLUME_NAME"/victimplay/"$RUN_NAME"/victims/ \
    "$@"
fi
