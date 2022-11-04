#!/bin/bash
# Usage: $0 OUTPUT_DIR NUM_GAMES VICTIM ADVERSARY
#
# If NUM_GAMES is -1, then the number of games from `match-base.cfg` will be
# used.

OUTPUT_DIR=$1
NUM_GAMES=$2

shift 2
if [ "${NUM_GAMES}" -ge 0 ]; then
  GAMES_OVERRIDE="-override-config numGamesTotal=${NUM_GAMES}"
fi
# Each replica of `match` should output to a different log file.
ID=$(openssl rand -hex 4)

mkdir --parents "${OUTPUT_DIR}"
# shellcheck disable=SC2068,SC2086
/engines/KataGo-custom/cpp/katago match \
  -config /go_attack/configs/match-base.cfg \
  -config /go_attack/configs/compute/1gpu.cfg \
  -sgf-output-dir "${OUTPUT_DIR}"/sgfs \
  -log-file "${OUTPUT_DIR}"/match-"${ID}".log \
  $GAMES_OVERRIDE $@
