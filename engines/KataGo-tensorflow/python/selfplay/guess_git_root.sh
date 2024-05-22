#!/bin/bash -eu

# if was not set externally, try to check with git
if [ -z ${GITROOTDIR+x} ]; then
   GITROOTDIR="$(git rev-parse --show-toplevel)" || true
fi
# if both external value and git guess failed we cannot run at all
if [ -z ${GITROOTDIR} ]; then
   echo "Either specify GITROOTDIR or run from the repo"
   exit 1
fi
GITROOTDIR="$(realpath "$GITROOTDIR")"
