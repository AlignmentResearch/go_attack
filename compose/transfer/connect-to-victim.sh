#!/bin/bash
# Connects to a Docker container named `victim` on port 80. This is used for
# running transfer experiments where the victim is run on another container and
# exposed on a port.
# The port should already be exposed on the victim's container or else netcat
# will terminate immediately.

CONTAINER_NAME="victim"
PORT=80

nc ${CONTAINER_NAME} ${PORT}
