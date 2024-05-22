# Builds an image that can run KataGo's C++ binaries as well as run twogtp
# (located at /gogui/bin/gogui-twogtp).
#
# Since this image performs a multi-stage build based on
# ANONYMOUS_USERNAME/goatttack:cpp, that image should be rebuilt before
# rebuilding this image.
FROM ANONYMOUS_USERNAME/ANONYMOUS_REPO:cpp as cpp

COPY ./controllers/gogui /gogui
WORKDIR /gogui

# These gogui installation commands are copied from
# compose/transfer/twogtp/Dockerfile. Code changes here likely should be copied
# to the other Dockerfile as well.
# Modify ubuntu_setup.sh to play nice with Docker build
RUN sed --in-place 's/sudo apt install/apt install --assume-yes/' ./ubuntu_setup.sh
RUN apt-get update --quiet && ./ubuntu_setup.sh && apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /
