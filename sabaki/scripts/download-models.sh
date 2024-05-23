#!/bin/bash

GIT_ROOT=$(git rev-parse --show-toplevel)
rm -rf $GIT_ROOT/sabaki/models
mkdir -p $GIT_ROOT/sabaki/models/adv
mkdir -p $GIT_ROOT/sabaki/models/victims

# Download models

# cyclic-adv-s545065216-d136760487.bin.gz
wget --content-disposition 'https://drive.google.com/uc?export=download&id=1gwD0nQsuE7aD92YJ66l82qtXR97A_lt1' \
     -P $GIT_ROOT/sabaki/models/adv/ -q --show-progress

# pass-adv-s34090496-d8262123.bin.gz
wget --content-disposition 'https://drive.google.com/uc?export=download&id=1YMcLtSfqn8Qq05iyrisNBim8WtiPPKbx' \
     -P $GIT_ROOT/sabaki/models/adv/ -q --show-progress

wget --content-disposition 'https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b40c256-s11840935168-d2898845681.bin.gz' \
     -P $GIT_ROOT/sabaki/models/victims/ -q --show-progress
