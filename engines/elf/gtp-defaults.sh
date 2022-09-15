#!/bin/bash
# Run ELF OpenGo in GTP mode with the default parameters listed in the ELF
# README, except that `--resign_thres` is set to 0 instead of 0.05.
./gtp.sh /pretrained-model.bin --verbose --gpu 0 --num_block 20 --dim 256 \
  --mcts_puct 1.50 --batchsize 16 --mcts_rollout_per_batch 16 --mcts_threads 2 \
  --mcts_rollout_per_thread 8192 --resign_thres 0 --mcts_virtual_loss 1 \
  --loglevel warning
