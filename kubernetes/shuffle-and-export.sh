#!/bin/bash -eu

function assert_exists() {
  if [ ! -e "$1" ]; then
    echo "Error: $1 does not exist"
    exit 1
  fi
}

USE_GATING=0
USE_TORCHSCRIPT=0
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149).
# Flags must be specified before positional arguments.
while [ -n "${1-}" ]; do
  case $1 in
    # Use PyTorch for training rather than TensorFlow.
    --use-pytorch) USE_PYTORCH=1 ;;
    # Export models to C++ as TorchScript models instead of using KataGo's
    # default serialization.
    --use-torchscript) USE_TORCHSCRIPT=1 ;;
    # Set this flag if the gatekeeper is enabled.
    --gating) USE_GATING=1 ;;
    # Pre-seed with this training data as the source.
    # If the pre-seed source directory is formatted as `<some path>/t0-s*-d*`,
    # then all earlier directories with lower step count (s) in `<some path>/`
    # will also be included in the pre-seeding.
    --preseed) PRESEED_SRC=$2; shift ;;
    -*) echo "Unknown parameter passed: $1"; exit 1 ;;
    *) break ;;
  esac
  shift
done

RUN_NAME="$1"
VOLUME_NAME="$2"
shift
shift

if [ -n "${USE_PYTORCH:-}" ]; then
  cd /engines/KataGo-custom/python
else
  if [ "${USE_TORCHSCRIPT:-}" -eq 1 ]; then
    echo "Error: --use-pytorch is required if --use-torchscript is set."
    exit 1
  fi
  cd /engines/KataGo-tensorflow/python
  # KataGo-tensorflow's shuffle_and_export.sh script doesn't have the
  # TorchScript argument.
  USE_TORCHSCRIPT=""
fi

# not related to shuffle-and-export but we want some process to log this
/go_attack/kubernetes/log-git-commit.sh /"$VOLUME_NAME"/victimplay/"$RUN_NAME"

EXPERIMENT_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"
mkdir --parents "$EXPERIMENT_DIR"/selfplay

PRESEED_DST="$EXPERIMENT_DIR"/selfplay/prev-selfplay
if [ -n "${PRESEED_SRC:-}" ] && [ ! -d "$PRESEED_DST" ]; then
  PRESEED_SRC=$(realpath "$PRESEED_SRC")
  echo "$PRESEED_SRC" > "$EXPERIMENT_DIR"/selfplay/prev-selfplay-"$(date +%Y%m%d-%H%M%S)".log
  if [[ "$PRESEED_SRC" =~ -s([0-9]+)-d[0-9]+ ]]; then
    # Preseed data up to the step count listed in PRESEED_SRC.
    FINAL_STEP=${BASH_REMATCH[1]}
    mkdir --parents "$PRESEED_DST"
    PRESEED_SRC_PARENT=$(dirname "$PRESEED_SRC")
    for DIR in "$PRESEED_SRC_PARENT"/*/; do
      DIR_NAME=$(basename "$DIR")
      if [ "$DIR_NAME" = "prev-selfplay" ] || [ "$DIR_NAME" = "random" ]; then
        ln -s "$DIR" "$PRESEED_DST"
        assert_exists "$PRESEED_DST/$DIR_NAME"
      elif [[ "$DIR" =~ -s([0-9]+)-d[0-9]+ ]]; then
        STEP=${BASH_REMATCH[1]}
        if [ "$STEP" -lt "$FINAL_STEP" ]; then
          ln -s "$DIR" "$PRESEED_DST"
          assert_exists "$PRESEED_DST/$DIR_NAME"
        fi
      else
        echo "Skipping unrecognized pre-seed source: $DIR"
      fi
    done
  else
    ln -s "$PRESEED_SRC" "$PRESEED_DST"
  fi
fi

# shellcheck disable=SC2086
./selfplay/shuffle_and_export_loop.sh "$RUN_NAME" "$EXPERIMENT_DIR" /tmp 16 256 $USE_GATING $USE_TORCHSCRIPT "$@"
sleep infinity
