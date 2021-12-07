# To build, navigate to the *root* of this repo and run:
# docker build . -f compose/python/Dockerfile -t humancompatibleai/goattack:python

# KataGo is most stable with TF 1.15
# See https://github.com/lightvector/KataGo/blob/master/SelfplayTraining.md.
#
# TF 1.15 is most compatible with CUDA 10.0 and CUDNN 7.4
# See cuda compatibility: https://www.tensorflow.org/install/source#gpu.
FROM nvidia/cuda:10.0-cudnn7-runtime-ubuntu18.04

ENV DEBIAN_FRONTEND=noninteractive

# Install utilities
RUN apt-get update -q \
  && apt-get install -y \
  curl \
  git \
  sudo \
  tmux \
  unzip \
  vim \
  wget \
  # Clean up
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install Python 3.7, which is the latest version compatible with TF 1.15
# Following guide here: https://docs.python-guide.org/starting/install3/linux/
RUN apt-get update -q \
  && apt-get install -y software-properties-common \
  && add-apt-repository ppa:deadsnakes/ppa \
  && apt-get update -q \
  && apt-get install -y python3.7 python3.7-venv python3-pip \
  && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 42 \
  # Clean up
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Create virtualenv and 'activate' it by adjusting PATH.
# See https://pythonspeed.com/articles/activate-virtualenv-dockerfile/.
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install python requirements within virtualenv
RUN pip install --no-cache-dir --upgrade pip setuptools
COPY ./compose/python/requirements.txt /downloads/requirements.txt
RUN pip install --no-cache-dir -r /downloads/requirements.txt

# Copy over KataGo python files
COPY ./engines/KataGo-raw/python /engines/KataGo-raw/python

ENTRYPOINT ["bash"]
