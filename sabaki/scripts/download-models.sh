#!/bin/bash

GIT_ROOT=$(git rev-parse --show-toplevel)
mkdir -p $GIT_ROOT/models/adv
mkdir -p $GIT_ROOT/models/victims

# Download models
wget 'https://drive.google.com/uc?export=download&id=1Qktfjfr6YwplF50T-LMXkFK_qG1UXeiy' \
     -O $GIT_ROOT/models/adv/adv505h-s349284096-d87808728.bin.gz
wget 'https://drive.google.com/uc?export=download&id=1TDSwJ_i0CHF_Ksf7lOaQIorpMu976fja' \
     -O $GIT_ROOT/models/adv/adv505h-s497721856-d125043118.bin.gz
wget 'https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b40c256-s11840935168-d2898845681.bin.gz' \
     -O $GIT_ROOT/models/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz
