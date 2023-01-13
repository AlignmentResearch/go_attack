# Builds an image that can run KataGo's C++ binaries as well as run twogtp.
#
# Since this image performs a multi-stage build based on
# humancompatibleai/goatttack:cpp, that image should be rebuilt before
# rebuilding this image.
#
# Example usage of twogtp:
#     mkdir --parents /outputs/sgfs && \
#     /gogui/bin/gogui-twogtp \
#       -black '/engines/KataGo-raw/cpp/katago gtp -config /go_attack/configs/gtp-raw.cfg -model <victim model>' \
#       -white '/engines/KataGo-custom/cpp/katago gtp -config /go_attack/configs/gtp-amcts.cfg -model <adversary model> -victim-model <victim model>' \
#       -alternate -auto -games <number of games> -komi 6.5 -maxmoves 1600 \
#       -sgffile /outputs/sgfs/game -verbose \
#     2>&1 | tee --append /outputs/twogtp.log
FROM humancompatibleai/goattack:cpp as cpp

COPY ./controllers/gogui /gogui
WORKDIR /gogui
# Modify ubuntu_setup.sh to play nice with Docker build
RUN sed --in-place 's/sudo apt install/apt install --assume-yes/' ./ubuntu_setup.sh
RUN apt-get update --quiet && ./ubuntu_setup.sh && apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /
