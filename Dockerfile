# To just build the base:
# docker build --target base -t humancompatibleai/goattack:base .
# To mount in source code:
# docker run -v /home/yawen/go_attack:/goattack --rm -it humancompatibleai/goattack:base
# To build everything:
# docker build -t humancompatibleai/goattack:latest .
# To run everything:
# docker run --runtime=nvidia -v /home/yawen/go_attack:/goattack -it humancompatibleai/goattack:latest

 
# Dockerfile, Image, Container
FROM nvidia/cuda:10.1-cudnn7-devel-ubuntu18.04 AS base
 
 
# Package Installation
RUN apt-get update -q \
   && DEBIAN_FRONTEND=noninteractive apt-get install -y \
   build-essential \
   curl \
   git \
   gconf2 \
   libgl1-mesa-dev \
   libgl1-mesa-glx \
   libglew-dev \
   libosmesa6-dev \
   libssl-dev \
   software-properties-common \
   net-tools \
   unzip \
   vim \
   sudo \
   virtualenv \
   wget \
   xpra \
   xserver-xorg-dev \
   libxrandr2 \
   libxss1 \
   libxcursor1 \
   libxcomposite1 \
   libasound2 \
   libxi6 \
   libxtst6 \
   libegl1-mesa  \
   xvfb \
   rsync \
   gcc \
   tmux \
   zlib1g-dev \
   libzip-dev \
   && apt-get clean \
   && rm -rf /var/lib/apt/lists/*
 
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
 
FROM base as binary-req
 
# Installing Java for GoGUI
RUN add-apt-repository ppa:webupd8team/java \
    && apt install -y openjdk-11-jre-headless \
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

