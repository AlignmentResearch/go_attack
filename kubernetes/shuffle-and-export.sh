#!/bin/bash -e
cd /engines/KataGo-custom/python
BASE_DIR="$1" # containing selfplay data and models and related directories
NAMEPREFIX="$2" # Displayed to users when KataGo loads the model

mkdir -p "$BASE_DIR"

selfplay_cmd=(
    ./selfplay/shuffle_and_export_loop.sh
    "$NAMEPREFIX"
    "$BASE_DIR"
    /tmp # scratch space, ideally on fast local disk, unique to this loop
    16   # nthreads
    256  # batchsize
    0    # whether to use gatekeeper
)
"${selfplay_cmd[@]}" # run command from array (https://stackoverflow.com/a/27196266/1337463)

# shuffle_and_export_loop.sh disowns subprocesses and exits.
# We sleep at the end so the container doesn't exit.
sleep infinity
