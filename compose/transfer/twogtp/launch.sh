# command for katago:
#   docker run --detach --interactive --gpus \"device=0\" --volume /home/${USER}/go_attack:/go_attack humancompatibleai/goattack:cpp /engines/KataGo-custom/cpp/katago gtp -config /go_attack/configs/gtp.cfg  -model /dev/null -victim-model /dev/null
# command for leela:
#   docker run --detach --interactive --gpus \"device=0\" --volume <tuning file> humancompatibleai/goattack:leela ./run-gtp.sh
# command for elf:
#   docker run --detach --interactive --gpus \"device=0\" humancompatibleai/goattack:elf ./run-gtp.sh
#
# ok so i guess i should write a command line utility out of this?
#   args:
#     - gpu (i think it's ok to just specify one, eh)
#     - komi
#       NOTE: ELF /requires/ komi=7.5, make sure to enforce this
#   args: num-games
#   opponent: leela or elf (we'll enforce that the other party is always katago adversary)
#   katago-model
#   katago-victim-model
#   katago config
#   output-dir
#
#  TODO(tomtseng) forgot about elf not allowing suicide --- can i toggle this in gtp.cfg?
#    I can turn off multi-stone suicide but i'm not sure that's the same thing
#    --- maybe check logic in katago's board.cpp
#
#  TODO(tomtseng) investigate: twogtp's -alternate flag docs: "Black and White
#  are exchanged every odd game; the scores saved in the results table -sgffile
#  are still using the name Black and White as given with -black and -white."
#  Need to check SGF files to make sure I can figure out who is who

NUM_GAMES=2
# output directory
HOST_OUTPUT_DIR=~/go_attack/sgfs

# Location of socket on the host. This path is the default path for Docker run
# in rootless mode.
HOST_DOCKER_SOCKET=/run/user/${UID}/docker.sock
# Handles case where Docker is run not in rootless mode.
[ ! -e ${HOST_DOCKER_SOCKET} ] && HOST_DOCKER_SOCKET=/var/run/docker.sock

export HOST_REPO_ROOT=$(git rev-parse --show-toplevel)
export HOST_LEELA_TUNING_FILE=${HOST_REPO_ROOT}/engines/leela/leelaz_opencl_tuning
touch -a ${HOST_LEELA_TUNING_FILE}

# We start the GTP instances first and have gogui-twogtp attach to them. If
# gogui-twogtp started the GTP instances, then gogui-twogtp would start feeding
# commands to them before they were ready.
BLACK_ID=$(docker run --detach --interactive --gpus \"device=0\" --volume ${HOST_LEELA_TUNING_FILE}:/root/.local/share/leela-zero/leelaz_opencl_tuning humancompatibleai/goattack:leela ./run-gtp.sh --debug)
WHITE_ID=$(docker run --detach --interactive --gpus \"device=0\" humancompatibleai/goattack:elf ./run-gtp.sh --debug)
# WHITE_ID=$(docker run --detach --interactive --gpus \"device=0\" --volume /home/${USER}/go_attack:/go_attack humancompatibleai/goattack:cpp /engines/KataGo-custom/cpp/katago gtp -config /go_attack/configs/gtp.cfg  -model /dev/null -victim-model /dev/null)


docker run --rm --volume ${HOST_DOCKER_SOCKET}:/var/run/docker.sock \
  --volume ${HOST_OUTPUT_DIR}:/output \
  humancompatibleai/goattack:twogtp bin/gogui-twogtp \
  -black "docker attach ${BLACK_ID}" -white "docker attach ${WHITE_ID}" \
  -alternate -auto -games ${NUM_GAMES} -komi 6.5 -sgffile /output/game \
  -verbose

docker rm --force ${BLACK_ID} ${WHITE_ID}
