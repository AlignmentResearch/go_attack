#!/bin/sh
cd /nbelrose/go_attack/engines/KataGo-custom
/engines/KataGo-custom/cpp/katago victimplay  -output-dir /nbelrose/outputs/victimplay  -models-dir /nbelrose/outputs/models  -nn-victim-file /nbelrose/go_attack/models/kata1-b40c256-s11840935168-d2898845681.bin.gz  -config /nbelrose/go_attack/configs/test/victimplay1.cfg