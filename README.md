# Go Attack

This repository contains code for studying the adversarial robustness of KataGo.

View our website here: https://go-defense.netlify.app/

To run our adversary with Sabaki, see [this guide](sabaki/README.md).

# Development / testing information

To clone this repository,
run one of the following commands
```
# Via HTTPS
git clone --recurse-submodules https://github.com/ANONYMOUS_USERNAME/ANONYMOUS_REPO.git

# Via SSH
git clone --recurse-submodules git@github.com:ANONYMOUS_USERNAME/ANONYMOUS_REPO.git
```

You can run `pip install -e .[dev]` inside the project root directory to install all necessary dependencies.

To run a pre-commit script before each commit, run `pre-commit install` (`pre-commit` should already have been installed in the previous step).
You may also want to run `pre-commit install` from `engines/KataGo-custom` to install that repository's respective commit hook.

## Git submodules

Modifications to KataGo *are not* tracked in this repository and should instead be made to the [ANONYMOUS_USERNAME/KataGo-custom](https://github.com/ANONYMOUS_USERNAME/KataGo-custom) repository. We use code from KataGo-custom in this repository via a Git submodule.

- [engines/KataGo-custom](engines/KataGo-custom) tracks the `stable` branch of the `KataGo-custom` repository.
- [engines/KataGo-raw](engines/KataGo-raw) tracks the `master` branch of https://github.com/lightvector/KataGo.

(For this anonymous repo, these are not actually submodules, as the anonymizer
app does not support submodules.)

## Individual containers

We run KataGo within Docker containers.
More specifically:
1. The C++ portion of KataGo runs in the container defined by [compose/cpp/Dockerfile](compose/cpp/Dockerfile).
2. The Python training portion of KataGo runs in the container defined at [compose/python/Dockerfile](compose/python/Dockerfile).

The Dockerfiles contain instructions for how to build them individually. This is useful if you want to test just one of the docker containers.

A KataGo executable can be found in the `/engines/KataGo-custom/cpp` directory inside the container.
To run a docker container, you can use a command like
```
docker run --gpus all -v ~/ANONYMOUS_REPO:/ANONYMOUS_REPO -it ANONYMOUS_USERNAME/ANONYMOUS_REPO:cpp
```

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
