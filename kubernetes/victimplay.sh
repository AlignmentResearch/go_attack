#!/bin/sh
/engines/KataGo-custom/cpp/katago victimplay \
    -output-dir /shared/victimplay/$1 \
    -models-dir /shared/adversaries/ \
    -nn-victim-file /shared/victims/kata1-b20c256x2-s5303129600-d1228401921.bin.gz \
    -config /shared/configs/active-experiment.cfg
