# To build, navigate to the *root* of this repo and run:
# docker build . -f compose/cpp/Dockerfile -t humancompatibleai/goattack:cpp
#
# Commands to build alternative targets:
# docker build . -f compose/cpp/Dockerfile -t humancompatibleai/goattack:cpp-build-deps --target build-*
#
# KataGo has been tested on CUDA 11.1 with CUDNN 8.0.4
# See https://github.com/lightvector/KataGo/blob/master/Compiling.md.
FROM nvcr.io/nvidia/tensorrt:22.07-py3 AS build-deps

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
  gdb \
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
RUN cmake . -DUSE_BACKEND=TENSORRT -DUSE_TCMALLOC=1 -DNO_GIT_REVISION=1
RUN make clean && make -j

FROM build-deps as build-custom
COPY ./engines/KataGo-custom/cpp /engines/KataGo-custom/cpp
WORKDIR /engines/KataGo-custom/cpp
RUN cmake . -DUSE_BACKEND=TENSORRT -DUSE_TCMALLOC=1 -DNO_GIT_REVISION=1
RUN make clean && make -j

FROM build-deps as build-custom-debug
COPY ./engines/KataGo-custom/cpp /engines/KataGo-custom/cpp
WORKDIR /engines/KataGo-custom/cpp
RUN cmake . -DUSE_BACKEND=TENSORRT -DUSE_TCMALLOC=1 -DNO_GIT_REVISION=1 -DBUILD_DEBUG=1
RUN make clean && make -j

FROM nvcr.io/nvidia/tensorrt:22.07-py3 AS runtime-deps

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
  rsync \
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
  # Clean up
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Reset working directory
WORKDIR /

FROM runtime-deps as debug
COPY --from=build-custom-debug /engines/KataGo-custom/cpp/katago /engines/KataGo-custom/cpp/katago

FROM runtime-deps as prod
COPY --from=build-raw /engines/KataGo-raw/cpp/katago /engines/KataGo-raw/cpp/katago
COPY --from=build-custom /engines/KataGo-custom/cpp/katago /engines/KataGo-custom/cpp/katago
