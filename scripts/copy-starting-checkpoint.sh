#!/bin/bash

EXP_ROOT="/nas/ucb/tony/go-attack/training/mcts/cp127-vis600-warmstart"
CKPT_DIR="/nas/ucb/tony/go-attack/checkpoints/katagotraining.org/b20c256x2-s5303129600-d1228401921"

######################### Copy files into train ##############################
INIT_WEIGHT_DIR="$EXP_ROOT/train/t0/initial_weights"
mkdir -p "$INIT_WEIGHT_DIR"

cp -v -- "$CKPT_DIR/saved_model/model.config.json" "$EXP_ROOT/train/t0/"

VAR_DIR="$CKPT_DIR/saved_model/variables"
pushd $VAR_DIR
for f in *; do
    cp -v -- "$VAR_DIR/$f" "$INIT_WEIGHT_DIR/model.$f";
done
popd
##############################################################################

######################### Copy files into models #############################
mkdir -p "$EXP_ROOT/models"
rm -rf "$EXP_ROOT/models/t0-s0-d0"
cp -rv -- "$CKPT_DIR" "$EXP_ROOT/models/t0-s0-d0"
##############################################################################
