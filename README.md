# Go Attack

This repository contains code for studying the adversarial robustness of KataGo.

Read about our research here: https://arxiv.org/abs/2211.00241.

View our website here: https://goattack.far.ai/.

To run our adversary with Sabaki, see [this guide](sabaki/README.md).

# Development / testing information

To clone this repository,
run one of the following commands
```
# Via HTTPS
git clone --recurse-submodules https://github.com/AlignmentResearch/go_attack.git 

# Via ssh
git clone --recurse-submodules git@github.com:AlignmentResearch/go_attack.git
```

## Git submodule: KataGo-custom

Modifications to KataGo *are not* tracked in this repository and should instead be made to the [AlignmentResearch/KataGo-custom](https://github.com/AlignmentResearch/KataGo-custom) repository. We use code from KataGo-custom in this repository via Git submodules.

KataGo-custom has the following significant branches:

- `KataGo-custom/stable` contains our changes to the stable version of KataGo.
- `KataGo-custom/master` tracks https://github.com/lightvector/KataGo.

## Other setup

You can run `pip install -e .[dev]` inside the project root directory to install all necessary dependencies.

To run a pre-commit script before each commit, run `pre-commit install` (`pre-commit` should already have been installed in the previous step).
You may also want to run `pre-commit install` from `engines/KataGo-custom` to install that repository's respective commit hook.

## Individual containers

We run KataGo within Docker containers.
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

## Website and analysis notebooks

See [AlignmentResearch/KataGoVisualizer](https://github.com/AlignmentResearch/KataGoVisualizer).

# Baseline attacks

In addition to the learned attacks, we also implement 5 baseline, hardcoded attacks:
- Edge attack, which plays random vertices in the outermost available ring of the board
- Random attack, which simply plays random legal moves
- Pass attack, which always passes at every turn
- Spiral attack, which deterministically plays the "largest" legal move in lexicographical order in polar coordinates (going counterclockwise starting from the outermost ring)
- [Mirror Go](https://en.wikipedia.org/wiki/Mirror_Go), which plays the opponent's last move reflected about the y = x diagonal, or the y = -x diagonal if they play on y = x. If the mirrored vertex is taken, then the policy plays the "closest" legal vertex by L1 distance.

You can test these attacks by running `baseline_attacks.py` with the appropriate `--strategy` flag (`edge`, `random`, `pass`, `spiral`, or `mirror`). Run `python scripts/baseline_attacks.py --help` for more information about all the available flags.
