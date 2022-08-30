# Go Attack

This repository contains code for studying the adversarial robustness of KataGo.

## Git submodule: KataGo-custom

Modifications to KataGo *are not* tracked in this repository. Rather they should be made to the [HumanCompatibleAI/KataGo-custom](https://github.com/HumanCompatibleAI/KataGo-custom) repository. We use code from KataGo-custom in this repository via git submodules.

KataGo-custom has the following significant branches:

- `KataGo-custom/stable` contains our changes to the stable version of KataGo.
- `KataGo-custom/master` tracks https://github.com/lightvector/KataGo.

# Development / testing

You can run `pip install -e .[dev]` inside the project root directory to install all necessary dependencies.

To run a pre-commit script before each commit, run `pre-commit install` (`pre-commit` should already have been installed in the previous step).

## Individual containers

We run KataGo within docker containers.
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

# Prerequisite & Dependencies

- **Summary**: For this project, we use **Docker** and **GitHub** repo to set up the dependencies and environment.
- **Docker image**: HumanCompatibleAI/go_attack:latest
- **GitHub repo**:
    - Project code: https://github.com/HumanCompatibleAI/go_attack
    - Agent code: https://github.com/HumanCompatibleAI/KataGo-custom
    - Controller code: https://github.com/Remi-Coulom/gogui/tree/v1.5.1
- **Setting up**
    - Download the repo
        - `git clone --recurse-submodules https://github.com/HumanCompatibleAI/go_attack.git`
        - `cd go_attack && mkdir games`
    - Build C++ and Python docker containers, and run the C++ container. A KataGo executable can be found in the `/engines/KataGo-custom/cpp` directory inside the container.
        - `docker build . -f compose/cpp/Dockerfile -t humancompatibleai/goattack:cpp`
        - `docker build . -f compose/python/Dockerfile -t humancompatibleai/goattack:python`
        - `docker run --gpus all -v ~/go_attack:/go_attack -it humancompatibleai/goattack:cpp`
    - Setup the controller
        - `cd /go_attack/controllers/gogui`
        - `git checkout tags/v1.5.1`
        - `./ubuntu_setup.sh`
    - Download model weights
        - `cd /go_attack/configs/katago && wget -i model_list.txt -P /go_attack/models`
    - Test if the installation is successful
        - `cd /engines/KataGo-custom/cpp/ && CUDA_VISIBLE_DEVICES=2 ./katago benchmark -model /go_attack/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz -config /go_attack/configs/katago/gtp_custom.cfg`

# Baseline attacks

In addition to the learned attacks, we also implement 5 baseline, hardcoded attacks:
- Edge attack, which plays random vertices in the outermost available ring of the board
- Random attack, which simply plays random legal moves
- Pass attack, which always passes at every turn
- Spiral attack, which deterministically plays the "largest" legal move in lexicographical order in polar coordinates (going counterclockwise starting from the outermost ring)
- [Mirror Go](https://en.wikipedia.org/wiki/Mirror_Go), which plays the opponent's last move reflected about the y = x diagonal, or the y = -x diagonal if they play on y = x. If the mirrored vertex is taken, then the policy plays the "closest" legal vertex by L1 distance.

You can test these attacks by running `baseline_attacks.py` with the appropriate `--strategy` flag (`edge`, `random`, `pass`, `spiral`, or `mirror`). Run `python scripts/baseline_attacks.py --help` for more information about all the available flags.
