#!/bin/sh
/engines/KataGo-custom/cpp/katago victimplay \
    -output-dir /shared/victimplay/"$1"/selfplay/ \
    -models-dir /shared/adversaries/ \
    -nn-victim-file "$2" \
    -config /shared/configs/active-experiment.cfg
