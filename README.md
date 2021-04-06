# Go Attack

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
    - `git checkout tags/v1.5.1`
    - `apt-get update && apt install gconf2 -y`
    - `./ubuntu_setup.sh`
    - `./install.sh -p /usr/local -j /usr/lib/jvm/java-11-openjdk-amd64`
- Compile KataGo
    - `cd /goattack/engines/KataGo-custom/`
    - `git checkout -b attack`
    - `cd /goattack/engines/KataGo-custom/cpp/`
    - `cmake312 . -DUSE_BACKEND=CUDA -DBUILD_DISTRIBUTED=1`
    - `make`
- Get the model weights
    - `cd /goattack/models`
    - `wget https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b40c256-s7186724608-d1743537710.bin.gz`
    - `wget https://github.com/lightvector/KataGo/releases/download/v1.4.5/g170-b30c320x2-s4824661760-d1229536699.bin.gz`
    - `wget https://github.com/lightvector/KataGo/releases/download/v1.4.5/g170-b40c256x2-s5095420928-d1229425124.bin.gz`
    - `wget https://github.com/lightvector/KataGo/releases/download/v1.4.5/g170e-b20c256x2-s5303129600-d1228401921.bin.gz`
- Test if the installation is successful
    - `cd /goattack/engines/KataGo-custom/cpp/ && ./katago benchmark -model /goattack/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz -config /goattack/configs/katago/gtp_custom.cfg`
    - `CUDA_VISIBLE_DEVICES=0,1 /goattack/scripts/battle.sh -e test -t 2 -n 2 -o -b gtp_black.cfg -w gtp_white.cfg`
- Make changes to cpp code and then make the cpp code
    - `make`