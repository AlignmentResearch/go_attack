#!/bin/sh
cd /engines/KataGo-custom/python || exit
./selfplay/train.sh    /shared/victimplay/"$1"    t0    b6c96    256    main    -lr-scale 1.0    -max-train-bucket-per-new-data 4