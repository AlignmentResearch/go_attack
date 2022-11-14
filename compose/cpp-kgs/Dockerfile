# To build, navigate to the *root* of this repo and run:
# docker build . -f compose/cpp/Dockerfile -t humancompatibleai/goattack:cpp
#
# Commands to build alternative targets:
# docker build . -f compose/cpp/Dockerfile -t humancompatibleai/goattack:cpp-build-deps --target build-*
#
# KataGo has been tested on CUDA 11.1 with CUDNN 8.0.4
# See https://github.com/lightvector/KataGo/blob/master/Compiling.md.
FROM nvidia/cuda:11.1.1-cudnn8-devel-ubuntu20.04 AS build-deps

ENV DEBIAN_FRONTEND=noninteractive

# Update Nvidia signing key
RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/3bf863cc.pub

# Add focal-proposed for libc6 patch
# See https://wiki.ubuntu.com/Testing/EnableProposed for details.
RUN echo "deb http://archive.ubuntu.com/ubuntu focal-proposed main" >> /etc/apt/sources.list \
 && echo "Package: *"                                               >> /etc/apt/preferences \
 && echo "Pin: release a=focal-proposed"                            >> /etc/apt/preferences \
 && echo "Pin-Priority: 400"                                        >> /etc/apt/preferences

# Install apt packages
RUN apt-get update -q \
  && apt-get install -y \
  # Utilities
  curl \
  git \
  sudo \
  tmux \
  unzip \
  vim \
  wget \
  # Packages needed to compile KataGo/cpp
  gcc \
  gdb \
  libgoogle-perftools-dev \
  libssl-dev \
  libzip-dev \
  zlib1g-dev \
  # Newer version of glibc without a deadlock bug:
  # https://bugs.launchpad.net/ubuntu/+source/glibc/+bug/1899800
  libc6=2.31-0ubuntu9.9 \
  libc6-dev=2.31-0ubuntu9.9 \
  libc-dev-bin=2.31-0ubuntu9.9 \
  # Clean up
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install cmake
# Instructions from https://cliutils.gitlab.io/modern-cmake/chapters/intro/installing.html
RUN wget -qO- "https://cmake.org/files/v3.22/cmake-3.22.0-linux-x86_64.tar.gz" \
  | tar --strip-components=1 -xz -C /usr/local

# Copy over KataGo cpp files and compile.
# See https://github.com/lightvector/KataGo/blob/master/Compiling.md.

FROM build-deps as build-raw
COPY ./engines/KataGo-raw/cpp /engines/KataGo-raw/cpp
WORKDIR /engines/KataGo-raw/cpp
RUN cmake . -DUSE_BACKEND=CUDA -DUSE_TCMALLOC=1 -DNO_GIT_REVISION=1
RUN make clean && make -j

FROM build-deps as build-custom
COPY ./engines/KataGo-custom/cpp /engines/KataGo-custom/cpp
WORKDIR /engines/KataGo-custom/cpp
RUN cmake . -DUSE_BACKEND=CUDA -DUSE_TCMALLOC=1 -DNO_GIT_REVISION=1
RUN make clean && make -j

FROM build-deps as build-custom-debug
COPY ./engines/KataGo-custom/cpp /engines/KataGo-custom/cpp
WORKDIR /engines/KataGo-custom/cpp
RUN cmake . -DUSE_BACKEND=CUDA -DUSE_TCMALLOC=1 -DNO_GIT_REVISION=1 -DBUILD_DEBUG=1
RUN make clean && make -j

# Actual production image, without development headers.
FROM nvidia/cuda:11.1.1-cudnn8-runtime-ubuntu20.04 AS runtime-deps

ENV DEBIAN_FRONTEND=noninteractive

# Update Nvidia signing key
RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/3bf863cc.pub

# Add focal-proposed for libc6 patch
# See https://wiki.ubuntu.com/Testing/EnableProposed for details.
RUN echo "deb http://archive.ubuntu.com/ubuntu focal-proposed main" >> /etc/apt/sources.list \
 && echo "Package: *"                                               >> /etc/apt/preferences \
 && echo "Pin: release a=focal-proposed"                            >> /etc/apt/preferences \
 && echo "Pin-Priority: 400"                                        >> /etc/apt/preferences

# Install useful apt packages
RUN apt-get update -q \
  && apt-get install -y \
  # Utilities
  cron \
  curl \
  gdb \
  git \
  gpustat \
  htop \
  netcat \
  python3 \
  python3-pip \
  rsync \
  socat \
  sudo \
  tmux \
  unzip \
  uuid-runtime \
  vim \
  wget \
  # KataGo runtime libraries
  libgoogle-perftools4 \
  libssl1.1 \
  libzip5 \
  zlib1g \
  # Newer version of glibc without a deadlock bug:
  # https://bugs.launchpad.net/ubuntu/+source/glibc/+bug/1899800
  libc6=2.31-0ubuntu9.9 \
  openjdk-11-jre-headless \
  # Clean up
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Reset working directory
WORKDIR /

# Install Python packages
RUN python3 -m pip install --upgrade pip

RUN mkdir -p /go_attack/src
COPY ./kubernetes/ /go_attack/kubernetes
COPY ./scripts/ /go_attack/scripts
COPY ./src/go_attack /go_attack/src/go_attack
COPY ./setup.py /go_attack/setup.py
COPY README.md /go_attack/README.md
COPY ./engines/kgs-bot/ /go_attack/engines/kgs-bot
# Silence annoying pip warning about running it as root inside the container
RUN pip install -e /go_attack --root-user-action=ignore

COPY /engines/KataGo-custom/cpp/evaluate_loop.sh /engines/KataGo-custom/cpp/evaluate_loop.sh

FROM runtime-deps as debug
COPY --from=build-custom-debug /engines/KataGo-custom/cpp/katago /engines/KataGo-custom/cpp/katago
COPY ./configs /go_attack/configs

FROM runtime-deps as prod
# Make the git commit visible to the image if provided as a --build-arg
ARG ARG_GIT_COMMIT
ENV GIT_COMMIT=$ARG_GIT_COMMIT

COPY --from=build-raw /engines/KataGo-raw/cpp/katago /engines/KataGo-raw/cpp/katago
COPY --from=build-custom /engines/KataGo-custom/cpp/katago /engines/KataGo-custom/cpp/katago

COPY ./configs /go_attack/configs

RUN mkdir /go_attack/adversary_models
RUN mkdir /go_attack/victim_models
RUN wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate $URL -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1Qktfjfr6YwplF50T-LMXkFK_qG1UXeiy" -O /go_attack/adversary_models/adversary_model.bin.gz && rm -rf /tmp/cookies.txt
RUN wget https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b40c256-s11840935168-d2898845681.bin.gz -O /go_attack/victim_models/victim_model.bin.gz