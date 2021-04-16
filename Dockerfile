# To just build the base:
# docker build --target base -t kmdanielduan/goattack:base .
# To mount in source code:
# docker run --runtime=nvidia -v /home/yawen/go_attack:/goattack --rm -it kmdanielduan/goattack:base
# To build everything:
# docker build -t kmdanielduan/goattack:latest .
# To run everything:
# docker run --runtime=nvidia -v /home/yawen/go_attack:/goattack -it kmdanielduan/goattack:latest

 
# Dockerfile, Image, Container
FROM nvidia/cuda:10.1-cudnn7-devel-ubuntu18.04 AS base
 
 
# Package Installation
RUN apt-get update -q \
   && DEBIAN_FRONTEND=noninteractive apt-get install -y \
   build-essential \
   software-properties-common \
   gcc \
   gdb \
   tmux \
   sudo \
   unzip \
   vim \
   virtualenv \
   wget \
   gconf2 \
   curl \
   libssl-dev \
   libzip-dev \
   && apt-get clean \
   && rm -rf /var/lib/apt/lists/*
 
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
 
FROM base as binary-req
 
# Installing updated version of packages 
RUN add-apt-repository ppa:webupd8team/java \
    && add-apt-repository -y ppa:git-core/ppa \
    && apt install -y openjdk-11-jre-headless \
    git \
    && apt-get clean 

# Installing cmake for compiling KataGo
WORKDIR /base
RUN wget https://github.com/Kitware/CMake/releases/download/v3.12.4/cmake-3.12.4-Linux-x86_64.tar.gz \
&& tar -xvf cmake-3.12.4-Linux-x86_64.tar.gz \
&& cd cmake-3.12.4-Linux-x86_64 \
&& apt install

RUN echo "alias cmake312='/base/cmake-3.12.4-Linux-x86_64/bin/cmake'" >> /root/.bashrc

WORKDIR /goattack

ENTRYPOINT ["bash"]

