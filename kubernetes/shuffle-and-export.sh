#!/bin/sh
cd /engines/KataGo-custom/python || exit
./selfplay/shuffle_and_export_loop.sh    "$1"    /shared/victimplay/"$2"    /tmp    16    256    0
sleep infinity