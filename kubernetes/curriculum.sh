#!/bin/sh -e

# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149).
# Flags must be specified before positional arguments.
while [ -n "${1-}" ]; do
  case $1 in
    # Directory where curriculum looks for victim models.
    --input-models-dir) INPUT_MODELS_DIR=$2; shift ;;
    -*) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
    *) break ;;
  esac
  shift
done

RUN_NAME="$1"
VOLUME_NAME="$2"
CURRICULUM_FILE="$3"
shift
shift
shift

INPUT_MODELS_DIR=${INPUT_MODELS_DIR:-/"$VOLUME_NAME"/victims}
python /engines/KataGo-custom/python/curriculum.py \
    -selfplay-dir=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/selfplay/ \
    -input-models-dir="$INPUT_MODELS_DIR" \
    -output-models-dir=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"/victims \
    -config-json-file="$CURRICULUM_FILE" \
    "$@"

sleep infinity
