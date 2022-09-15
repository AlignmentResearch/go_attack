#!/bin/bash
# Runs ELF OpenGO in GTP mode with reasonable default parameters.

function usage() {
  echo "Usage: $0 [-d] [-v]"
  echo "  -d, --debug    Run faster but worse for debugging purposes"
  echo "  -v, --verbose  Print verbose output"
}

# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while [[ "$#" -gt 0 ]]; do
  case $1 in
    -d|--d) FAST=1 ;;
    -h|--help) usage; exit 0 ;;
    -v|--verbose) VERBOSE=1 ;;
    *) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
  esac
  shift
done

# Parameters for ELF OpenGo. If FAST is not set, then we're running ELF with
# the default parameters listed in the ELF README, except that `--resign_thres`
# is set to 0 instead of 0.05.
FLAGS="\
  --gpu 0 \
  --num_block 20 \
  --dim 256 \
  --mcts_puct 1.50 \
  --resign_thres 0 \
  --mcts_virtual_loss 1 \
"

if [[ -n "${FAST}" ]]; then
  FLAGS+="\
    --batchsize 1 \
    --mcts_rollout_per_batch 1 \
    --mcts_threads 1 \
    --mcts_rollout_per_thread 1 \
  "
else
  FLAGS+="\
    --batchsize 16 \
    --mcts_rollout_per_batch 16 \
    --mcts_threads 2 \
    --mcts_rollout_per_thread 8192 \
  "
fi

if [[ -n "${VERBOSE}" ]]; then
  FLAGS+="--verbose"
else
  FLAGS+="--loglevel warning"
fi

./gtp.sh /pretrained-model.bin ${FLAGS}
