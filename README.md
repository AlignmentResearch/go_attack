# Go Attack

This repository contains code for studying the adversarial robustness of KataGo.

## Git submodule: KataGo-custom

Modifications to KataGo *are not* tracked in this repository. Rather they should be made to the [HumanCompatibleAI/KataGo-custom](https://github.com/HumanCompatibleAI/KataGo-custom) repository. We use code from KataGo-custom in this repository via git submodules.

KataGo-custom has the following significant branches:

- `KataGo-custom/stable` is the latest stable version of KataGo that we run baselines with.
- `KataGo-custom/victimplay` contains code related to victimplay.
- `KataGo-custom/master` tracks https://github.com/lightvector/KataGo.

# Development / testing on svm

The instructions here require the dependencies in `dev_requirements.txt` to run.
On `svm`, you can `conda activate katago` to get all these dependencies.

## Individual containers

We run KataGo within a docker containers.
More specifically:
1. The C++ portion of KataGo runs in the container defined by [compose/cpp/Dockerfile](compose/cpp/Dockerfile).
2. The Python training portion of KataGo runs in the container defined at [compose/python/Dockerfile](compose/python/Dockerfile).

The Dockerfiles contain instructions for how to build them individually. This is useful if you want to test just one of the docker containers.

## Docker compose
Within the `compose` directory of this repo are a few docker-compose `.yml` files
that automate the process of spinning up the various components of training.

Each `.yml` file also has a corresponding `.env` that configures more specific
parameters of the run (
    e.g. what directory to write to,
    how many threads to use,
    batch size,
    where to look for other config files
).

# Helpful notebooks
- [notebooks/sgf-explorer.ipynb](notebooks/sgf-explorer.ipynb) loads self/victim-play games into a pandas dataframe and lets you do some data analysis. One thing I use this file for is to pick out specific games I then load into a visualizer.
 - [notebooks/victimplay-log-analysis.ipynb](notebooks/victimplay-log-analysis.ipynb) let's you analyze victimplay logs. It is less powerful that the sgf-explorer (i.e. has less info), but runs much faster.

These notebooks require the dependencies in `dev_requirements.txt` to run.

# Prerequisite & Dependencies

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
