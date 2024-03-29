#!/bin/bash

function usage() {
  echo "Usage: $0 [-d] [-v]"
  echo
  echo "Runs Leela Zero in GTP mode with reasonable default parameters."
  echo
  echo "  -d, --debug    Run faster but worse for debugging purposes"
  echo "  -v, --verbose  Print verbose output"
}

# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while [[ "$#" -gt 0 ]]; do
  case $1 in
    -d|--debug) FAST=1 ;;
    -h|--help) usage; exit 0 ;;
    -v|--verbose) VERBOSE=1 ;;
    *) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
  esac
  shift
done

FLAGS="--noponder --resignpct 0"
if [[ -n "${FAST}" ]]; then
  FLAGS+="\
    --playouts 1 \
    --timemanage fast \
    --visits 1 \
  "
else
  # It's not documented at what settings Leela plays at a superhuman
  # level. We'll guess that 40k visits is sufficient.
  FLAGS+="\
    --timelimit 0 \
    --visits 40000 \
  "
fi
if [[ -z "${VERBOSE}" ]]; then
  FLAGS+="--quiet"
fi

./leelaz --gtp ${FLAGS}
