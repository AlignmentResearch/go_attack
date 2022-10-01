BLACK_COMMAND="docker run --gpus \"device=0\" -v /home/${USER}/go_attack:/go_attack -t humancompatibleai/goattack:cpp /engines/KataGo-custom/cpp/katago gtp -config /go_attack/configs/gtp.cfg  -model /dev/null -victim-model /dev/null"
WHITE_COMMAND=${BLACK_COMMAND}
NUM_GAMES=1
OUTPUT_DIR=/tmp

# Location of socket on the host. This path is the default path for Docker run
# in rootless mode.
HOST_DOCKER_SOCKET=/run/user/${UID}/docker.sock
# Handles case where Docker is run not in rootless mode.
[ ! -e ${HOST_DOCKER_SOCKET} ] && HOST_DOCKER_SOCKET=/var/run/docker.sock

docker run -v ${HOST_DOCKER_SOCKET}:/var/run/docker.sock \
  humancompatibleai/goattack:twogtp \
  bin/gogui-twogtp -black "${BLACK_COMMAND}" -white "${WHITE_COMMAND}" \
  -alternate -auto -games ${NUM_GAMES} -komi 6.5 -sgffile ${OUTPUT_DIR}/ \
  -verbose

# I think twogtp is sending the "protocol_version" message while docker is still
# launching and katago isn't ready? katago never sees the msg so twogtp just
# hangs on the first message
# TODO(tomtseng) let's try this: first launch the katago containers. then
# gogui-gtp's -black/white command will consist of attaching to the containers?

