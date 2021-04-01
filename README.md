# KataGo

* [Overview](#overview)
* [Setting Up and Running](#setting-up-and-running)

## Overview

TODO

## Setting Up and Running

- Download the repo
    - `git clone https://github.com/kmdanielduan/go_attack.git`
    - `mkdir games models`
- Setup the docker image and container
    - make sure you are in svm.bair.berkeley.edu (TODO: change to pulling images from Docker Hub in the future)
    - `docker run --runtime=nvidia -v /path/to/goattack:/goattack -it humancompatibleai/goattack:latest`
- Setup the controller
    - `cd /goattack/controller/gogui`
    - `apt-get update && apt install gconf2 -y`
    - `./ubuntu_setup.sh`
    - `./install.sh -p /usr/local -j /usr/lib/jvm/java-11-openjdk-amd64`
- Compile KataGo
    - `cd /goattack/engines/KataGo/cpp/ /base/cmake-3.12.4-Linux-x86_64/bin/cmake . -DUSE_BACKEND=CUDA -DBUILD_DISTRIBUTED=1`
    - `make`
- Get the model weights
    - `cd /goattack/models`
    - `wget https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b40c256-s7186724608-d1743537710.bin.gz`
    - `wget https://github.com/lightvector/KataGo/releases/download/v1.4.5/g170-b30c320x2-s4824661760-d1229536699.bin.gz`
    - `wget https://github.com/lightvector/KataGo/releases/download/v1.4.5/g170-b40c256x2-s5095420928-d1229425124.bin.gz`
    - `wget https://github.com/lightvector/KataGo/releases/download/v1.4.5/g170e-b20c256x2-s5303129600-d1228401921.bin.gz`
- Test if the installation is successful
    - `./katago benchmark -model /goattack/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz -config /goattack/configs/katago/gtp_custom.cfg`