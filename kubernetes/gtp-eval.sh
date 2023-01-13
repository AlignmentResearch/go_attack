#!/bin/bash

RUN_NAME=$1
NUM_GAMES=100

mkdir --parents "$RUN_NAME/sgfs" && \
/gogui/bin/gogui-twogtp \
  -black '/engines/KataGo-raw/cpp/katago gtp -config /go_attack/configs/gtp-raw.cfg -model /shared/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz' \
  -white '/engines/KataGo-custom/cpp/katago gtp -config /go_attack/configs/gtp-amcts.cfg -model /shared/victimplay/ttseng-avoid-pass-alive-coldstart-39-20221025-175949/models/t0-s545065216-d136760487/model.bin.gz -victim-model /shared/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz' \
  -alternate -auto -games "$NUM_GAMES" -komi 6.5 -maxmoves 1600 \
  -sgffile /outputs/sgfs/game -verbose \
2>&1 | tee --append "$RUN_NAME/twogtp.log"

