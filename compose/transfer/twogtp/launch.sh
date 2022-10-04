NUM_GAMES=1
OUTPUT_DIR=/tmp

# Location of socket on the host. This path is the default path for Docker run
# in rootless mode.
HOST_DOCKER_SOCKET=/run/user/${UID}/docker.sock
# Handles case where Docker is run not in rootless mode.
[ ! -e ${HOST_DOCKER_SOCKET} ] && HOST_DOCKER_SOCKET=/var/run/docker.sock

# We start the GTP instances first and have gogui-twogtp attach to them. If
# gogui-twogtp started the GTP instances, then gogui-twogtp would start feeding
# commands to them before they were ready.
BLACK_ID=$(docker run --detach --interactive --gpus \"device=0\" --volume /home/${USER}/go_attack:/go_attack humancompatibleai/goattack:cpp /engines/KataGo-custom/cpp/katago gtp -config /go_attack/configs/gtp.cfg  -model /dev/null -victim-model /dev/null)
WHITE_ID=$(docker run --detach --interactive --gpus \"device=0\" --volume /home/${USER}/go_attack:/go_attack humancompatibleai/goattack:cpp /engines/KataGo-custom/cpp/katago gtp -config /go_attack/configs/gtp.cfg  -model /dev/null -victim-model /dev/null)

docker run -v ${HOST_DOCKER_SOCKET}:/var/run/docker.sock \
  humancompatibleai/goattack:twogtp bin/gogui-twogtp \
  -black "docker attach ${BLACK_ID}" -white "docker attach ${WHITE_ID}" \
  -alternate -auto -games ${NUM_GAMES} -komi 6.5 -sgffile ${OUTPUT_DIR}/ \
  -verbose

docker rm --force ${BLACK_ID} ${WHITE_ID}
