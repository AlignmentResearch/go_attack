#!/bin/bash

GIT_ROOT=$(git rev-parse --show-toplevel)
rm -rf $GIT_ROOT/sabaki/models
mkdir -p $GIT_ROOT/sabaki/models/adv
mkdir -p $GIT_ROOT/sabaki/models/victims

# Download a few models

# Original cyclic adversary
mkdir -p $GIT_ROOT/sabaki/models/adv/cyclic
wget --content-disposition 'https://drive.google.com/uc?export=download&id=1O2zD1HpxpaPKeRLPuSSUMmznkgM0HeXO' \
     -P $GIT_ROOT/sabaki/models/adv/cyclic -q --show-progress

# pass-adv-s34090496-d8262123.bin.gz
mkdir -p $GIT_ROOT/sabaki/models/adv/pass
wget --content-disposition 'https://drive.google.com/uc?export=download&id=17xW8sFjmh7W3VOfR3_vNv9dk4ndJ9wBC' \
     -P $GIT_ROOT/sabaki/models/adv/pass -q --show-progress

wget --content-disposition 'https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b40c256-s11840935168-d2898845681.bin.gz' \
     -P $GIT_ROOT/sabaki/models/victims/ -q --show-progress
