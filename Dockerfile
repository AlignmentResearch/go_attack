# To just build the base:
# docker build --target base -t humancompatibleai/goattack:base .
# To mount in source code:
# docker run --runtime=nvidia -v /home/yawen/goattack:/goattack --rm -it humancompatibleai/goattack:base
# To build everything:
# docker build -t humancompatibleai/goattack:latest .
# To run everything:
# docker run --runtime=nvidia -v /home/yawen/goattack:/goattack -it humancompatibleai/goattack:latest 
# docker run --runtime=nvidia --privileged -v /home/yawen/goattack:/goattack -d -it humancompatibleai/goattack:latest 

 
# Dockerfile, Image, Container

# FROM nvidia/cuda:10.1-cudnn7-devel-ubuntu18.04 AS base
FROM nvidia/cuda:10.0-cudnn7-devel-ubuntu18.04 AS base

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
   python3-dev \ 
   python3-pip \ 
   python3-venv \
   sshfs \
#    virtualenv \
   wget \
   gconf2 \
   curl \
   libssl-dev \
   libzip-dev \
   && apt-get clean \
   && rm -rf /var/lib/apt/lists/*
 
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

FROM base AS binary-req

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

# pip install all python dependencies
# RUN python3 -m venv --system-site-packages /base/venv 
# RUN virtualenv --system-site-packages --python=python3 venv

COPY python-requirements.txt ./
# RUN /base/venv/bin/pip3 install --upgrade pip setuptools
# RUN /base/venv/bin/pip3 install --no-cache-dir -r python-requirements.txt
RUN pip3 install --upgrade pip setuptools
RUN pip3 install --no-cache-dir -r python-requirements.txt

WORKDIR /goattack

ENTRYPOINT ["bash"]
