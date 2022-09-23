#!/bin/sh
cd /engines/KataGo-custom/python || exit
RUN_NAME="$1"
VOLUME_NAME="$2"
mkdir -p /"$VOLUME_NAME"/victimplay/"$RUN_NAME"
./selfplay/train.sh    /"$VOLUME_NAME"/victimplay/"$RUN_NAME"    t0    b6c96    256    main    -lr-scale 1.0    -max-train-bucket-per-new-data 4