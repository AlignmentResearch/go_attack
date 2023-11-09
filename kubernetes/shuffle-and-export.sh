#!/bin/bash -eu

USE_GATING=0
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149).
# Flags must be specified before positional arguments.
while [ -n "${1-}" ]; do
  case $1 in
    # Set this flag if the gatekeeper is enabled.
    --gating) USE_GATING=1 ;;
    # Set this to preseed training data with data up to and including this
    # directory. This should be a */selfplay/t0-s*-d* directory.
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
mkdir --parents "$EXPERIMENT_DIR"

PRESEED_DST="$EXPERIMENT_DIR"/selfplay/prev-selfplay
if [ -n "${PRESEED_SRC:-}" ] && [ ! -d "$PRESEED_DST" ]; then
  if [[ "$PRESEED_SRC" =~ t0-s([0-9]+)-d[0-9]+ ]]; then
    FINAL_STEP=${BASH_REMATCH[1]}
  else
    echo "Can't parse step count from $PRESEED_SRC"
    exit 1
  fi

  mkdir --parents "$PRESEED_DST"
  PRESEED_SRC=$(realpath "$PRESEED_SRC")
  PRESEED_SRC_PARENT=$(dirname "$PRESEED_SRC")
  for DIR in "$PRESEED_SRC_PARENT"/*/; do
    DIR_NAME=$(basename "$DIR")
    if [ "$DIR_NAME" = "prev-selfplay" ] || [ "$DIR_NAME" = "random" ]; then
      ln -s "$DIR" "$PRESEED_DST"
    elif [[ "$DIR" =~ t0-s([0-9]+)-d[0-9]+ ]]; then
      STEP=${BASH_REMATCH[1]}
      if [ "$STEP" -le "$FINAL_STEP" ]; then
        ln -s "$DIR" "$PRESEED_DST"
      fi
    else
      echo "Skipping unrecognized pre-seed source: $DIR"
    fi
  done
fi

cd /engines/KataGo-custom/python
./selfplay/shuffle_and_export_loop.sh "$RUN_NAME" "$EXPERIMENT_DIR" /tmp 16 256 $USE_GATING $@
sleep infinity
