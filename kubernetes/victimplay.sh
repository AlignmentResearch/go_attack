#!/bin/sh
mkdir -p /shared/victimplay/"$1"
/engines/KataGo-custom/cpp/katago victimplay \
    -output-dir /shared/victimplay/"$1"/selfplay/ \
    -models-dir /shared/models/ \
    -nn-victim-path /shared/victims/ \
    -config /shared/configs/active-experiment.cfg \
    -config /shared/configs/compute/1gpu.cfg
