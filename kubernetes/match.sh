#!/bin/bash

OUTPUT_DIR=$1
NUM_GAMES=$2
shift; shift
if [ "${NUM_GAMES}" -lt 0 ]; then
  GAMES_OVERRIDE="-override-config numGamesTotal=${NUM_GAMES}"
fi
mkdir --parents "${OUTPUT_DIR}"
# shellcheck disable=SC2068,SC2086
/engines/KataGo-custom/cpp/katago match \
  -config /go_attack/configs/match-base.cfg \
  -config /go_attack/configs/compute/1gpu.cfg \
  -sgf-output-dir "${OUTPUT_DIR}"/sgfs \
  -log-file "${OUTPUT_DIR}"/match.log \
  $GAMES_OVERRIDE $@
