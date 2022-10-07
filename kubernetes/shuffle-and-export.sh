#!/bin/bash -e
cd /engines/KataGo-custom/python
RUN_NAME="$1"
DIRECTORY="$2"
VOLUME_NAME="$3"
mkdir -p /"$VOLUME_NAME"/victimplay/"$DIRECTORY"
./selfplay/shuffle_and_export_loop.sh    "$RUN_NAME"    /"$VOLUME_NAME"/victimplay/"$DIRECTORY"    /tmp    16    256    0
sleep infinity