#!/bin/bash

OUTPUT_DIR=$1

mkdir --parents ${OUTPUT_DIR}

/engines/KataGo-custom/cpp/katago match \
  -config /go_attack/configs/match-base.cfg \
  -config /go_attack/configs/compute/1gpu.cfg \
  -sgf-output-dir ${OUTPUT_DIR}/sgfs \
  -log-file ${OUTPUT_DIR}/match.log
