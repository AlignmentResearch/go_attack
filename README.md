# Go Attack

* [Overview](#overview)
* [Prerequisite & Dependencies](#prerequisite-&-dependencies)

## Overview

TODO

## Prerequisite & Dependencies

- **Summary**: For this project, we use **Docker** and **GitHub** repo to set up the dependencies and environment.
- **Docker image**: kmdanielduan/goattack:latest
- **GitHub repo**:
    - Project code: https://github.com/kmdanielduan/go_attack
    - Agent code: https://github.com/kmdanielduan/KataGo-custom
    - Controller code: https://github.com/Remi-Coulom/gogui/tree/v1.5.1
- **Setting up**
    - Download the repo 
        - `git clone --recurse-submodules https://github.com/kmdanielduan/go_attack.git goattack`
        - `cd goattack && mkdir games`
    - Pull the docker image and build container
        - `docker pull kmdanielduan/goattack:latest`
        - `docker run --runtime=nvidia -v ~/goattack:/goattack -it kmdanielduan/goattack:latest `
    - Setup the controller
        - `cd /goattack/controllers/gogui`
        - `git checkout tags/v1.5.1`
        - `./ubuntu_setup.sh`
    - Compile KataGo agent
        - `cd /goattack/engines/KataGo-custom/`
        - `git checkout --track origin/attack`
        - `cd /goattack/engines/KataGo-custom/cpp/`
        - `cmake312 . -DUSE_BACKEND=CUDA -DBUILD_DISTRIBUTED=1`
        - `make`
    - Download models weights
        - `cd /goattack/configs/katago && wget -i model_list.txt -P /goattack/models`
    - Test if the installation is successful
        - `cd /goattack/engines/KataGo-custom/cpp/ && CUDA_VISIBLE_DEVICES=2 ./katago benchmark -model /goattack/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz -config /goattack/configs/katago/gtp_custom.cfg`
        - `python3 /goattack/scripts/attack.py -b gtp_black.cfg -w gtp_white.cfg -bp 50 -wp 50 -t 1 --komi 7 --size 9 --n 10 -e test/test-code --gpu 1 2 3`
