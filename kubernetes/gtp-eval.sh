#!/bin/bash -eu

OUTPUT_DIR=$1
NUM_GPUS=$2
NUM_GAMES=100
GPU_CONFIG="go_attack/configs/compute/${NUM_GPUS}gpu.cfg"
VICTIM_MODEL=/shared/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz

/go_attack/kubernetes/log-git-commit.sh "$OUTPUT_DIR"

mkdir --parents "$OUTPUT_DIR/sgfs" && \
/gogui/bin/gogui-twogtp \
  -black "/engines/KataGo-raw/cpp/katago gtp -config /go_attack/configs/gtp-raw.cfg -config $GPU_CONFIG -model $VICTIM_MODEL" \
  -white "/engines/KataGo-custom/cpp/katago gtp -config /go_attack/configs/gtp-amcts.cfg -config $GPU_CONFIG -model /shared/victimplay/ttseng-avoid-pass-alive-coldstart-39-20221025-175949/models/t0-s545065216-d136760487/model.bin.gz -victim-model $VICTIM_MODEL" \
  -alternate -auto -games "$NUM_GAMES" -komi 6.5 -maxmoves 1600 \
  -sgffile "$OUTPUT_DIR/sgfs/game" -verbose \
2>&1 | tee --append "$OUTPUT_DIR/twogtp.log"
