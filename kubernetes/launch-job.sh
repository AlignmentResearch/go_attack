#!/bin/sh
ctl job run --container \
    humancompatibleai/goattack:cpp \
    humancompatibleai/goattack:python \
    humancompatibleai/goattack:python \
    --volume_name nbelrose \
    --volume_mount nbelrose \
    --command /nbelrose/go_attack/kubernetes/victimplay.sh \
    /nbelrose/go_attack/kubernetes/train.sh \
    /nbelrose/go_attack/kubernetes/shuffle-and-export.sh \
    --gpu 2 1 1 \
    --name go-training