# Builds an image that can run Leela Zero. An OpenCL-compatible GPU is needed
# for Leela Zero, so use the `--gpus` flag when running this image with `docker
# run`.
#
# Run `./run-gtp` inside the Docker container to play against
# Leela Zero via GTP.

FROM nvidia/opencl:devel-ubuntu18.04 AS build-deps

RUN apt-get update --quiet \
 && apt-get install --assume-yes \
  cmake \
  g++ \
  git \
  libboost-dev \
  libboost-filesystem-dev \
  libboost-program-options-dev \
  zlib1g-dev \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN git clone --depth=1 --branch=v0.0.1 --recurse-submodules \
  --shallow-submodules https://github.com/AlignmentResearch/leela-zero
WORKDIR leela-zero/build
RUN cmake .. && cmake --build . -- -j16


FROM nvidia/opencl:runtime-ubuntu18.04 AS runtime-deps
COPY --from=build-deps /leela-zero/build/ /leela-zero/build/

RUN apt-get update --quiet \
 && apt-get install --assume-yes \
  libboost-filesystem-dev \
  libboost-program-options-dev \
  socat \
  wget \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Download weights to the Leela Zero's default directory for weights. A
# collection of weights is available at https://zero.sjeng.org/
RUN mkdir --parents /root/.local/share/leela-zero \
  && wget --output-document=/root/.local/share/leela-zero/best-network \
  https://zero.sjeng.org/networks/0e9ea880fd3c4444695e8ff4b8a36310d2c03f7c858cadd37af3b76df1d1d15f.gz
WORKDIR /leela-zero/build/
COPY run-gtp.sh .
