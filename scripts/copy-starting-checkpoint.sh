#!/bin/bash

EXP_ROOT="/nas/ucb/tony/go-attack/training/emcts1.5/cp127-vis32-perfect-sim-warmstart"
CKPT_DIR="/nas/ucb/tony/go-attack/training/emcts1-v4/cp127-vis32-apt-no-vtimeloss-v200/models/t0-s90054400-d22562213"

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
