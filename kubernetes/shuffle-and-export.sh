#!/bin/bash -e

USE_TORCHSCRIPT=0
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149).
# Flags must be specified before positional arguments.
while [ -n "${1-}" ]; do
  case $1 in
    # Use PyTorch for training rather than TensorFlow.
    --use-pytorch) USE_PYTORCH=1 ;;
    # Export models to C++ as TorchScript models instead than using KataGo's
    # default serialization.
    --use-torchscript) USE_TORCHSCRIPT=1 ;;
    -*) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
    *) break ;;
  esac
  shift
done

RUN_NAME="$1"
DIRECTORY="$2"
VOLUME_NAME="$3"
# 1 to enable gatekeeper, 0 to disable gatekeeper
USE_GATING="$4"

if [ -n "${USE_PYTORCH:-}" ]; then
  cd /engines/KataGo-custom/python
else
  if [ "${USE_TORCHSCRIPT:-}" -eq 1 ]; then
    echo "Error: --use-pytorch is required if --use-torchscript is set."
    exit 1
  fi
  cd /engines/KataGo-tensorflow/python
fi

# not related to shuffle-and-export but we want some process to log this
/go_attack/kubernetes/log-git-commit.sh /"$VOLUME_NAME"/victimplay/"$DIRECTORY"

mkdir -p /"$VOLUME_NAME"/victimplay/"$DIRECTORY"
./selfplay/shuffle_and_export_loop.sh    "$RUN_NAME"    /"$VOLUME_NAME"/victimplay/"$DIRECTORY"    /tmp    16    256    $USE_GATING    $USE_TORCHSCRIPT
sleep infinity
