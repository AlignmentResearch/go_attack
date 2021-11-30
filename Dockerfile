# To just build the base:
# docker build --target base -t humancompatibleai/goattack:base .
# To mount in source code:
# docker run --runtime=nvidia -v /home/yawen/goattack:/goattack --rm -it humancompatibleai/goattack:base
# To build everything:
# docker build -t humancompatibleai/goattack:latest .
# To run everything:
# docker run --runtime=nvidia -v /home/yawen/goattack:/goattack -it humancompatibleai/goattack:latest
# docker run --runtime=nvidia --privileged -v /home/yawen/goattack:/goattack -d -it humancompatibleai/goattack:latest

# See https://catalog.ngc.nvidia.com/orgs/nvidia/containers/tensorflow
# And https://docs.nvidia.com/deeplearning/frameworks/tensorflow-release-notes/rel_21-11.html
FROM nvcr.io/nvidia/tensorflow:21.11-tf1-py3 AS base

# Install packages
RUN apt-get update -q \
   && DEBIAN_FRONTEND=noninteractive apt-get install -y \
   # Utilities
   curl \
   git \
   gpustat \
   sudo \
   tmux \
   unzip \
   vim \
   wget \
   # Packages below needed to build KataGo
   gcc \
   gdb \
   zlib1g-dev \
   libzip-dev \
   libssl-dev \
   libgoogle-perftools-dev \
   # Finally clean up
   && apt-get clean \
   && rm -rf /var/lib/apt/lists/*

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

# Installing cmake for compiling KataGo
WORKDIR /base
RUN wget https://github.com/Kitware/CMake/releases/download/v3.22.0/cmake-3.22.0-linux-x86_64.tar.gz \
&& tar -xvf cmake-3.22.0-linux-x86_64.tar.gz \
&& cd cmake-3.22.0-linux-x86_64 \
&& apt install
RUN echo "alias cmake322='/base/cmake-3.22.0-linux-x86_64/bin/cmake'" >> /root/.bashrc

FROM base AS binary-req

# Install python requirements
COPY python-requirements.txt ./
RUN pip3 install --upgrade pip setuptools
RUN pip3 install --no-cache-dir -r python-requirements.txt

WORKDIR /goattack

ENTRYPOINT ["bash"]
