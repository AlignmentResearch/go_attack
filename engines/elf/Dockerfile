# Builds an image that can run ELF OpenGo. A CUDA-compatible GPU is needed for
# ELF, so use the `--gpus` flags when running this image with `docker run`.
#
# Run `./run-gtp.sh` inside the Docker container to play against ELF OpenGo
# via GTP.

# ELF's README suggests using CUDA 10.0 and cuDNN 7. A6000 GPUs need CUDA
# 11, however, and CUDA 11 requires cuDNN 8.
FROM nvidia/cuda:11.6.2-cudnn8-devel-ubuntu18.04 as build-deps

RUN apt-get update --quiet \
 && apt-get install --assume-yes \
  cmake \
  g++ \
  gcc \
  git \
  libboost-all-dev \
  libzmq3-dev \
  wget \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN wget --output-document=install-conda.sh \
  https://repo.anaconda.com/miniconda/Miniconda3-py37_4.12.0-Linux-x86_64.sh
RUN bash install-conda.sh -p /conda -b
ENV PATH=/conda/bin:${PATH}
RUN conda install numpy zeromq pyzmq
RUN conda install pytorch cudatoolkit=11.6 -c pytorch -c conda-forge

# This fork of ELF fixes the code to work with newer versions of PyTorch that
# are the only versions compatible with CUDA 11 but that introduced a
# breaking change.
RUN git clone --depth=1 --branch=v0.0.1 --recurse-submodules \
  --shallow-submodules https://github.com/AlignmentResearch/ELF
WORKDIR ELF
RUN make -j16


FROM nvidia/cuda:11.6.2-cudnn8-runtime-ubuntu18.04 as runtime-deps
COPY --from=build-deps /ELF/ /ELF/
COPY --from=build-deps /conda/ /conda/
ENV PATH=/conda/bin:${PATH}

RUN apt-get update --quiet \
  && apt-get install --assume-yes \
  socat \
  wget \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# pretrained-go-19x19-v0 is likely the "prototype model" from the paper that won
# against professional players, whereas this v2 model is likely the final model
# from the paper.
RUN wget --output-document=pretrained-model.bin \
  https://github.com/pytorch/ELF/releases/download/pretrained-go-19x19-v2/pretrained-go-19x19-v2.bin

WORKDIR /ELF/scripts/elfgames/go/
COPY entrypoint.sh /
COPY run-gtp.sh .
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
