#!/bin/bash

GIT_ROOT=$(git rev-parse --show-toplevel)
mkdir -p $GIT_ROOT/models/adv
mkdir -p $GIT_ROOT/models/victims

# Download models

# adv505h-s349284096-d87808728.bin.gz
wget --content-disposition 'https://drive.google.com/uc?export=download&id=1Qktfjfr6YwplF50T-LMXkFK_qG1UXeiy' \
     -P $GIT_ROOT/models/adv/ --content-disposition

# adv505h-s497721856-d125043118.bin.gz
wget --content-disposition 'https://drive.google.com/uc?export=download&id=1TDSwJ_i0CHF_Ksf7lOaQIorpMu976fja' \
     -P $GIT_ROOT/models/adv/ --content-disposition

# adv505h-s545065216-d136760487.bin.gz
wget --content-disposition 'https://drive.google.com/uc?export=download&id=1gwD0nQsuE7aD92YJ66l82qtXR97A_lt1' \
     -P $GIT_ROOT/models/adv/

wget --content-disposition 'https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b40c256-s11840935168-d2898845681.bin.gz' \
     -P $GIT_ROOT/models/victims/
