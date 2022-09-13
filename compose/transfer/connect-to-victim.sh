#!/bin/bash
# Connects to a Docker container named `victim` on port 80. This is used for
# running transfer experiments where the victim is run on another container and
# exposed on a port.

CONTAINER_NAME="victim"
PORT=80

while ! nc -z ${CONTAINER_NAME} ${PORT} ; do
  echo "Waiting for port ${PORT}..."
  sleep 1
done

nc ${CONTAINER_NAME} ${PORT}
