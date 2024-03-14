#!/bin/bash -eu

if [ -z "$1" ]; then
    echo "Usage: $0 <integer>"
    exit 1
fi

OUTPUT_DIR=/shared/match/ttseng-vit-selfplay-240314/elo
for ((i=0; i<1000; i++)); do
    if [ $((i % 2)) -ne "$1" ]; then
        continue
    fi
    DONE_FILE=$OUTPUT_DIR/$i/finished
    if [ -f "$DONE_FILE" ]; then
        continue
    fi
    mkdir --parents $OUTPUT_DIR/$i
    /go_attack/kubernetes/match.sh $OUTPUT_DIR/$i "-1" -config /shared/ttseng/configs/sweeps/vit-selfplay/elo/configs/$i.cfg
    touch $DONE_FILE
done
