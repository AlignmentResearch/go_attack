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
#   remember to set multiStoneSuicideLegal = false
#
#  TODO(tomtseng) print warning about -alternate: "Black and White
#  are exchanged every odd game; the scores saved in the results table -sgffile
#  are still using the name Black and White as given with -black and -white."
# TODO write a script that can reverse results in the SGF files? ehhh this is
# lower priority, we can just look at .dat files for now maybe?

# also need to make sure each thread gets a separate sgf prefix
# TODO merge this with the other launch file

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
# BLACK_ID=$(docker run --detach --interactive --gpus \"device=0\" --volume ${HOST_LEELA_TUNING_FILE}:/root/.local/share/leela-zero/leelaz_opencl_tuning humancompatibleai/goattack:leela ./run-gtp.sh)
BLACK_ID=$(docker run --detach --interactive --gpus \"device=0\" humancompatibleai/goattack:elf ./run-gtp.sh)
WHITE_ID=$(docker run --detach --interactive --gpus \"device=0\" --volume /nas/ucb/ttseng/go_attack/models:/models --volume ${HOST_REPO_ROOT}/configs:/go_attack/configs humancompatibleai/goattack:cpp /engines/KataGo-custom/cpp/katago gtp -config /go_attack/configs/gtp.cfg  -model /models/adv/t0-s34090496-d8262123.bin.gz -victim-model /models/victim/cp505.bin.gz)


docker run --rm --volume ${HOST_DOCKER_SOCKET}:/var/run/docker.sock \
  --volume ${HOST_OUTPUT_DIR}:/output \
  humancompatibleai/goattack:twogtp bin/gogui-twogtp \
  -black "docker attach ${BLACK_ID}" -white "docker attach ${WHITE_ID}" \
  -alternate -auto -games ${NUM_GAMES} -komi 6.5 -maxmoves 1600 \
  -sgffile /output/game -verbose

docker rm --force ${BLACK_ID} ${WHITE_ID}
