# To build, navigate to the *root* of this repo and run:
# docker build . -f compose/python/Dockerfile -t humancompatibleai/goattack:python

# KataGo is most stable with TF 1.15
# See https://github.com/lightvector/KataGo/blob/master/SelfplayTraining.md.
#
# https://docs.nvidia.com/deeplearning/frameworks/tensorflow-release-notes/rel_22-01.html
FROM nvcr.io/nvidia/tensorflow:22.01-tf1-py3 AS build-deps

ENV DEBIAN_FRONTEND=noninteractive

# Install utilities
RUN apt-get update -q \
  && apt-get install -y \
  curl \
  git \
  python3-venv \
  sudo \
  tmux \
  unzip \
  uuid-runtime \
  vim \
  wget \
  # Clean up
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Create virtualenv and 'activate' it by adjusting PATH.
# See https://pythonspeed.com/articles/activate-virtualenv-dockerfile/.
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV --system-site-packages
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
# NVidia Dockerfile sets BASH_ENV to source bashrc always which causes some
# KataGo scripts to complain about unset PS1 -- unset this in the entrypoint.
RUN echo "unset BASH_ENV" > /opt/nvidia/entrypoint.d/01-unset_bash_env.sh

FROM build-deps as python-deps
# Install python requirements within virtualenv
RUN pip install --no-cache-dir --upgrade pip setuptools
COPY ./compose/python/requirements.txt /downloads/requirements.txt
RUN pip install --no-cache-dir -r /downloads/requirements.txt

FROM python-deps as prod
# Copy over KataGo python files
COPY ./engines/KataGo-raw/python /engines/KataGo-raw/python
COPY ./engines/KataGo-custom/python /engines/KataGo-custom/python

RUN mkdir -p /go_attack/src
COPY ./configs /go_attack/configs
COPY ./kubernetes /go_attack/kubernetes
COPY ./scripts/ /go_attack/scripts
COPY ./src/go_attack /go_attack/src/go_attack
COPY ./setup.py /go_attack/setup.py
COPY README.md /go_attack/README.md

# Make /engines/KataGo-* git repos to make scripts run nicely.
# TODO: Make this less hacky...
WORKDIR /engines/KataGo-raw
RUN git init . \
  && git add . \
  && git config user.name dummy_name \
  && git config user.email dummy@email.com \
  && git commit -m "Dummy commit"
WORKDIR /engines/KataGo-custom
RUN git init . \
  && git add . \
  && git config user.name dummy_name \
  && git config user.email dummy@email.com \
  && git commit -m "Dummy commit"

# Reset working directory
WORKDIR /
