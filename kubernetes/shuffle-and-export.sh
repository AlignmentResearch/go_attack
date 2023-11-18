#!/bin/bash -eu

USE_GATING=0
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149).
# Flags must be specified before positional arguments.
while [ -n "${1-}" ]; do
  case $1 in
    # Set this flag if the gatekeeper is enabled.
    --gating) USE_GATING=1 ;;
    # Pre-seed with this training data as the source.
    # If the pre-seed source directory is formatted as `*/selfplay/t0-s*-d*`,
    # then all earlier directories with lower step count (s) in `*/selfplay/`
    # will also be included in the pre-seeding.
    --preseed) PRESEED_SRC=$2; shift ;;
    -*) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
    *) break ;;
  esac
  shift
done

RUN_NAME="$1"
DIRECTORY="$2"
VOLUME_NAME="$3"
shift
shift
shift

# not related to shuffle-and-export but we want some process to log this
/go_attack/kubernetes/log-git-commit.sh /"$VOLUME_NAME"/victimplay/"$DIRECTORY"

EXPERIMENT_DIR=/"$VOLUME_NAME"/victimplay/"$DIRECTORY"
mkdir --parents "$EXPERIMENT_DIR"/selfplay

PRESEED_DST="$EXPERIMENT_DIR"/selfplay/prev-selfplay
if [ -n "${PRESEED_SRC:-}" ] && [ ! -d "$PRESEED_DST" ]; then
  PRESEED_SRC=$(realpath "$PRESEED_SRC")
  echo "$PRESEED_SRC" > "$EXPERIMENT_DIR"/selfplay/prev-selfplay-$(date +%Y%m%d-%H%M%S).log
  if [[ "$PRESEED_SRC" =~ -s([0-9]+)-d[0-9]+ ]]; then
    # Preseed data up to the step count listed in PRESEED_SRC.
    FINAL_STEP=${BASH_REMATCH[1]}
    mkdir --parents "$PRESEED_DST"
    PRESEED_SRC_PARENT=$(dirname "$PRESEED_SRC")
    for DIR in "$PRESEED_SRC_PARENT"/*/; do
      DIR_NAME=$(basename "$DIR")
      if [ "$DIR_NAME" = "prev-selfplay" ] || [ "$DIR_NAME" = "random" ]; then
        ln -s "$DIR" "$PRESEED_DST"
      elif [[ "$DIR" =~ -s([0-9]+)-d[0-9]+ ]]; then
        STEP=${BASH_REMATCH[1]}
        if [ "$STEP" -le "$FINAL_STEP" ]; then
          ln -s "$DIR" "$PRESEED_DST"
        fi
      else
        echo "Skipping unrecognized pre-seed source: $DIR"
      fi
    done
  else
    ln -s "$PRESEED_SRC" "$PRESEED_DST"
  fi
fi

cd /engines/KataGo-custom/python
./selfplay/shuffle_and_export_loop.sh "$RUN_NAME" "$EXPERIMENT_DIR" /tmp 16 256 $USE_GATING "$@"
sleep infinity
