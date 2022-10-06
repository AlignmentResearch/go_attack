# Builds an image that can run gogui's twogtp command for connecting two GTP
# engines to each other.
#
# Run `bin/gogui-twogtp` inside the container to run twogtp.

# After building this image as humancompatibleai/goattack:twogtp, use
# `launch.sh` to run an example twogtp match.

FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update --quiet \
  && apt-get install --assume-yes \
  git \
  netcat \
  wget \
  zip

# Install docker
RUN wget https://get.docker.com --output-document=get-docker.sh
RUN sh get-docker.sh

RUN git clone --depth=1 --branch=v1.5.1 https://github.com/Remi-Coulom/gogui
WORKDIR gogui

# Modify ubuntu_setup.sh to play nice with Docker build
RUN sed --in-place 's/sudo apt install/apt install --assume-yes/' ubuntu_setup.sh
# Build gogui
RUN ./ubuntu_setup.sh && apt-get clean && rm -rf /var/lib/apt/lists/*
