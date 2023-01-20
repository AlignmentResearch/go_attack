#!/bin/bash -eu
# Arguments:
# - Output directory
# - Number of GPUs
# - Number of games
# - Adversary config
# - Victim config
# - Adversary model
# - Victim model

OUTPUT_DIR=$1
NUM_GPUS=$2
NUM_GAMES=$3
ADV_CONFIG=$4
VICTIM_CONFIG=$5
ADV_MODEL=$6
VICTIM_MODEL=$7

GPU_CONFIG="go_attack/configs/compute/${NUM_GPUS}gpu.cfg"

/go_attack/kubernetes/log-git-commit.sh "$OUTPUT_DIR"

mkdir --parents "$OUTPUT_DIR/sgfs" && \
/gogui/bin/gogui-twogtp \
  -black "/engines/KataGo-raw/cpp/katago gtp -config $VICTIM_CONFIG -config $GPU_CONFIG -override-config logSearchInfo=true,logToStdout=true -model $VICTIM_MODEL" \
  -white "/engines/KataGo-custom/cpp/katago gtp -config $ADV_CONFIG -config $GPU_CONFIG --override-config logSearchInfo=true,logToStdout=true model $ADV_MODEL -victim-model $VICTIM_MODEL" \
  -alternate -auto -games "$NUM_GAMES" -komi 6.5 -maxmoves 1600 \
  -sgffile "$OUTPUT_DIR/sgfs/game" -verbose \
2>&1 | tee --append "$OUTPUT_DIR/twogtp.log"
