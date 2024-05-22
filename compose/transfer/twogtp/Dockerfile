# Builds an image that can run gogui's twogtp command for connecting two GTP
# engines to each other.
#
# Run `bin/gogui-twogtp` inside the container to run twogtp.

FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update --quiet \
  && apt-get install --assume-yes \
  git \
  netcat \
  wget \
  zip

RUN git clone --depth=1 --branch=v0.0.0 https://github.com/ANONYMOUS_USERNAME/gogui
WORKDIR gogui

# Code changes to these gogui installation commands likely should be copied to
# compose/cpp-and-twogtp/Dockerfile as well.
# Modify ubuntu_setup.sh to play nice with Docker build
RUN sed --in-place 's/sudo apt install/apt install --assume-yes/' ubuntu_setup.sh
# Build gogui
RUN ./ubuntu_setup.sh && apt-get clean && rm -rf /var/lib/apt/lists/*
