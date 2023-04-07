# %%
import sys
import os
import argparse
import traceback
import random
import math
import time
import re
import logging
import colorsys
import json
from interp.nb_common import GameState
import tensorflow as tf
import numpy as np
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib

from IPython.display import display, SVG

from typing import Optional, Tuple

try:
    go_attack_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
except NameError:
    go_attack_path = os.path.realpath(os.getcwd() + "/..")
    assert os.path.basename(go_attack_path) == "go_attack", "Don't know how to find the go_attack directory"

sys.path.insert(0, os.path.join(go_attack_path, "engines/KataGo-custom/python"))
sys.path.append("/usr/lib/python3.8/site-packages")
sys.path.append("/opt/venv/lib/python3.8/site-packages")

from board import Board
from model import Model
import common

# %% Load plotly
import plotly
import plotly.express as px

from IPython.display import Image, FileLink

import plotly.graph_objects as go
import plotly.io as pio
import plotly.tools as tls
import hashlib

import interp.nb_common
from interp.nb_common import GameState, load_model

interp.nb_common.set_plotly_renderer("png")

# %% Load model from saved files
POS_LEN = 19  # 19x19 board
model = load_model(pos_len=POS_LEN)
gs = GameState()

# %% Run the model and plot the activations

sess = tf.InteractiveSession()
model, model_outputs = load_model(pos_len=POS_LEN)
gs = GameState(POS_LEN, model=model, model_outputs=model_outputs)

policy = sess.run(model.policy_output, feed_dict=gs.feed_dict())
gs.show(policy[0, :, 0])

# %% Check which side is white or black

game = "B[hk];W[ik];B[hj];W[ij];B[om];W[hi];B[lp];W[gj];B[qq];W[gk]".split(";")

gs = GameState(POS_LEN, model=model)
for g in game:
    player = Board.BLACK if g[0] == "B" else Board.WHITE
    pos = (ord(g[2]) - ord("a"), ord(g[3]) - ord("a"))
    gs.play(player, pos)

outs = gs.get_outputs(sess, model)
gs.show(outs["policy0"])
gs.show(outs["policy1"])

# Looks like policy0 is black, which makes sense.

# %% Construct the two slightly different tricky positions

from pysgf import SGF


def sgf_to_gs(game):
    gs = GameState(board_size=int(game.get_list_property("SZ")[0]))
    for pos_str in game.get_list_property("AB"):
        pos = (ord(pos_str[0]) - ord("a"), ord(pos_str[1]) - ord("a"))
        gs.play(Board.BLACK, pos)
    for pos_str in game.get_list_property("AW"):
        pos = (ord(pos_str[0]) - ord("a"), ord(pos_str[1]) - ord("a"))
        gs.play(Board.WHITE, pos)

    node = game
    assert node.move is None

    while len(node.children) > 0:
        node = node.children[0]
        assert node.move is not None
        player = Board.BLACK if node.move.player == "B" else Board.WHITE
        loc = node.move.coords
        gs.play(player, (loc[0], 18 - loc[1]))

    return gs


gs_cycle = sgf_to_gs(SGF.parse_file("../connection_test_position_A_realgameCOdemo_losecyclewinanyways.sgf"))
gs_nocycle = sgf_to_gs(SGF.parse_file("../connection_test_position_B_realgameCOdemo_losecyclewinanyways.sgf"))

# %% Check winrate of the two positions


def print_scorebelief(gs, outputs):
    board = gs.board
    scorebelief = outputs["scorebelief"]
    scoremean = outputs["scoremean"]
    scorestdev = outputs["scorestdev"]
    sbscale = outputs["sbscale"]

    scorebelief = list(scorebelief)
    if board.pla != Board.WHITE:
        scorebelief.reverse()
        scoremean = -scoremean

    scoredistrmid = POS_LEN * POS_LEN + Model.EXTRA_SCORE_DISTR_RADIUS
    ret = ""
    ret += "TEXT "
    ret += "SBScale: " + str(sbscale) + "\n"
    ret += "ScoreBelief: \n"
    for i in range(17, -1, -1):
        ret += "TEXT "
        ret += "%+6.1f" % (-(i * 20 + 0.5))
        for j in range(20):
            idx = scoredistrmid - (i * 20 + j) - 1
            ret += " %4.0f" % (scorebelief[idx] * 10000)
        ret += "\n"
    for i in range(18):
        ret += "TEXT "
        ret += "%+6.1f" % ((i * 20 + 0.5))
        for j in range(20):
            idx = scoredistrmid + (i * 20 + j)
            ret += " %4.0f" % (scorebelief[idx] * 10000)
        ret += "\n"

    beliefscore = 0
    beliefscoresq = 0
    beliefwin = 0
    belieftotal = 0
    for idx in range(scoredistrmid * 2):
        score = idx - scoredistrmid + 0.5
        if score > 0:
            beliefwin += scorebelief[idx]
        else:
            beliefwin -= scorebelief[idx]
        belieftotal += scorebelief[idx]
        beliefscore += score * scorebelief[idx]
        beliefscoresq += score * score * scorebelief[idx]

    beliefscoremean = beliefscore / belieftotal
    beliefscoremeansq = beliefscoresq / belieftotal
    beliefscorevar = max(0, beliefscoremeansq - beliefscoremean * beliefscoremean)
    beliefscorestdev = math.sqrt(beliefscorevar)

    ret += "TEXT BeliefWin: %.2fc\n" % (100 * beliefwin / belieftotal)
    ret += "TEXT BeliefTotal: %.2fc\n" % (100 * belieftotal)
    ret += "TEXT BeliefScoreMean: %.1f\n" % (beliefscoremean)
    ret += "TEXT BeliefScoreStdev: %.1f\n" % (beliefscorestdev)
    ret += "TEXT ScoreMean: %.1f\n" % (scoremean)
    ret += "TEXT ScoreStdev: %.1f\n" % (scorestdev)
    ret += "TEXT Value: %s\n" % (str(outputs["value"]))
    ret += "TEXT TDValue: %s\n" % (str(outputs["td_value"]))
    ret += "TEXT TDValue2: %s\n" % (str(outputs["td_value2"]))
    ret += "TEXT TDValue3: %s\n" % (str(outputs["td_value3"]))
    ret += "TEXT TDScore: %s\n" % (str(outputs["td_score"]))
    ret += "TEXT Estv: %s\n" % (str(outputs["estv"]))
    ret += "TEXT Ests: %s\n" % (str(outputs["ests"]))
    return ret


print(print_scorebelief(gs_cycle, gs_cycle.get_outputs(sess, model)))
print(print_scorebelief(gs_nocycle, gs_nocycle.get_outputs(sess, model)))

# %%

cycle_ins = gs_cycle.feed_dict()[model.bin_inputs]
nocycle_ins = gs_nocycle.feed_dict()[model.bin_inputs]

batch, pos, chans = np.where(cycle_ins != nocycle_ins)

# %% [markdown]
"""
The differences are:
 - in positions (12, 7), (13, 7)
 - in features:
   - "area" (18, 19)
   - "liberties==3" (5)
     - Black group has 3 liberties, white group has 4+ liberties
   - "stone=pla/opp" (1, 2)


Other notes:
- Input channel 0 is all 1 always
"""
# %%

model_layers = dict(model.outputs_by_layer + model.other_internal_outputs)
print("Available model layers to look at:", list(model_layers.keys()))


# Available model layers to look at: ['conv1', 'rconv1/trans1', 'rconv1/conv1', 'rconv1/trans2', 'rconv1/conv2', 'rconv1',
# 'rconv2/trans1', 'rconv2/conv1', 'rconv2/trans2', 'rconv2/conv2', 'rconv2', 'rconv3/trans1', 'rconv3/conv1',
# 'rconv3/trans2', 'rconv3/conv2', 'rconv3', 'rconv4/trans1', 'rconv4/conv1', 'rconv4/trans2', 'rconv4/conv2', 'rconv4',
# 'rconv5/trans1', 'rconv5/conv1', 'rconv5/trans2', 'rconv5/conv2', 'rconv5', 'rconv6/trans1', 'rconv6/conv1a',
# 'rconv6/conv1b', 'rconv6/trans2', 'rconv6/conv2', 'rconv6', 'rconv7/trans1', 'rconv7/conv1', 'rconv7/trans2',
# 'rconv7/conv2', 'rconv7', 'rconv8/trans1', 'rconv8/conv1', 'rconv8/trans2', 'rconv8/conv2', 'rconv8', 'rconv9/trans1',
# 'rconv9/conv1', 'rconv9/trans2', 'rconv9/conv2', 'rconv9', 'rconv10/trans1', 'rconv10/conv1', 'rconv10/trans2',
# 'rconv10/conv2', 'rconv10', 'rconv11/trans1', 'rconv11/conv1a', 'rconv11/conv1b', 'rconv11/trans2', 'rconv11/conv2',
# 'rconv11', 'rconv12/trans1', 'rconv12/conv1', 'rconv12/trans2', 'rconv12/conv2', 'rconv12', 'rconv13/trans1',
# 'rconv13/conv1', 'rconv13/trans2', 'rconv13/conv2', 'rconv13', 'rconv14/trans1', 'rconv14/conv1', 'rconv14/trans2',
# 'rconv14/conv2', 'rconv14', 'rconv15/trans1', 'rconv15/conv1', 'rconv15/trans2', 'rconv15/conv2', 'rconv15',
# 'rconv16/trans1', 'rconv16/conv1a', 'rconv16/conv1b', 'rconv16/trans2', 'rconv16/conv2', 'rconv16', 'rconv17/trans1',
# 'rconv17/conv1', 'rconv17/trans2', 'rconv17/conv2', 'rconv17', 'rconv18/trans1', 'rconv18/conv1', 'rconv18/trans2',
# 'rconv18/conv2', 'rconv18', 'rconv19/trans1', 'rconv19/conv1', 'rconv19/trans2', 'rconv19/conv2', 'rconv19',
# 'rconv20/trans1', 'rconv20/conv1', 'rconv20/trans2', 'rconv20/conv2', 'rconv20', 'rconv21/trans1', 'rconv21/conv1a',
# 'rconv21/conv1b', 'rconv21/trans2', 'rconv21/conv2', 'rconv21', 'rconv22/trans1', 'rconv22/conv1', 'rconv22/trans2',
# 'rconv22/conv2', 'rconv22', 'rconv23/trans1', 'rconv23/conv1', 'rconv23/trans2', 'rconv23/conv2', 'rconv23',
# 'rconv24/trans1', 'rconv24/conv1', 'rconv24/trans2', 'rconv24/conv2', 'rconv24', 'rconv25/trans1', 'rconv25/conv1',
# 'rconv25/trans2', 'rconv25/conv2', 'rconv25', 'rconv26/trans1', 'rconv26/conv1a', 'rconv26/conv1b', 'rconv26/trans2',
# 'rconv26/conv2', 'rconv26', 'rconv27/trans1', 'rconv27/conv1', 'rconv27/trans2', 'rconv27/conv2', 'rconv27',
# 'rconv28/trans1', 'rconv28/conv1', 'rconv28/trans2', 'rconv28/conv2', 'rconv28', 'rconv29/trans1', 'rconv29/conv1',
# 'rconv29/trans2', 'rconv29/conv2', 'rconv29', 'rconv30/trans1', 'rconv30/conv1', 'rconv30/trans2', 'rconv30/conv2',
# 'rconv30', 'rconv31/trans1', 'rconv31/conv1a', 'rconv31/conv1b', 'rconv31/trans2', 'rconv31/conv2', 'rconv31',
# 'rconv32/trans1', 'rconv32/conv1', 'rconv32/trans2', 'rconv32/conv2', 'rconv32', 'rconv33/trans1', 'rconv33/conv1',
# 'rconv33/trans2', 'rconv33/conv2', 'rconv33', 'rconv34/trans1', 'rconv34/conv1', 'rconv34/trans2', 'rconv34/conv2',
# 'rconv34', 'rconv35/trans1', 'rconv35/conv1', 'rconv35/trans2', 'rconv35/conv2', 'rconv35', 'rconv36/trans1',
# 'rconv36/conv1a', 'rconv36/conv1b', 'rconv36/trans2', 'rconv36/conv2', 'rconv36', 'rconv37/trans1', 'rconv37/conv1',
# 'rconv37/trans2', 'rconv37/conv2', 'rconv37', 'rconv38/trans1', 'rconv38/conv1', 'rconv38/trans2', 'rconv38/conv2',
# 'rconv38', 'rconv39/trans1', 'rconv39/conv1', 'rconv39/trans2', 'rconv39/conv2', 'rconv39', 'rconv40/trans1',
# 'rconv40/conv1', 'rconv40/trans2', 'rconv40/conv2', 'rconv40', 'trunk', 'p1/intermediate_conv', 'g1/prenorm', 'g1',
# 'g2', 'g3', 'p1', 'p2', 'pass', 'v1/prenorm', 'v1', 'vownership', 'vscoring', 'futurepos', 'seki']


#   add_layer_visualizations("conv1",normalization_div=6)
#   add_layer_visualizations("rconv1",normalization_div=14)
#   add_layer_visualizations("rconv2",normalization_div=20)
#   add_layer_visualizations("rconv3",normalization_div=26)
#   add_layer_visualizations("rconv4",normalization_div=36)
#   add_layer_visualizations("rconv5",normalization_div=40)
#   add_layer_visualizations("rconv6",normalization_div=40)
#   add_layer_visualizations("rconv7",normalization_div=44)
#   add_layer_visualizations("rconv7/conv1a",normalization_div=12)
#   add_layer_visualizations("rconv7/conv1b",normalization_div=12)
#   add_layer_visualizations("rconv8",normalization_div=48)
#   add_layer_visualizations("rconv9",normalization_div=52)
#   add_layer_visualizations("rconv10",normalization_div=55)
#   add_layer_visualizations("rconv11",normalization_div=58)
#   add_layer_visualizations("rconv11/conv1a",normalization_div=12)
#   add_layer_visualizations("rconv11/conv1b",normalization_div=12)
#   add_layer_visualizations("rconv12",normalization_div=58)
#   add_layer_visualizations("rconv13",normalization_div=64)
#   add_layer_visualizations("rconv14",normalization_div=66)
#   add_layer_visualizations("g1",normalization_div=6)
#   add_layer_visualizations("p1",normalization_div=2)
#   add_layer_visualizations("v1",normalization_div=4)


# %% Look at the difference of the conv1 outputs

conv1_cycle = sess.run(model_layers["rconv40"], feed_dict=gs_cycle.feed_dict())
conv1_nocycle = sess.run(model_layers["rconv40"], feed_dict=gs_nocycle.feed_dict())

fig = px.imshow(
    (conv1_cycle - conv1_nocycle)[0, :, :, :],
    facet_col=2,
    facet_col_wrap=16,
    facet_row_spacing=0.02,
    color_continuous_scale="RdBu",
    zmin=-5,
    zmax=5,
)
fig.show()

# %% Look at the difference of the policy outputs (p2)

# trunk_cycle = sess.run(model_layers["trunk"], feed_dict=gs_cycle.feed_dict())
# trunk_nocycle = sess.run(model_layers["trunk"], feed_dict=gs_nocycle.feed_dict())

# fig = px.imshow(
#     (trunk_cycle - trunk_nocycle)[0, :, :, :],
#     facet_col=2,
#     facet_col_wrap=16,
#     facet_row_spacing=0.02,
#     color_continuous_scale="RdBu",
#     zmin=-10,
#     zmax=10,
# )
# fig.show()

# %%


def make_quilt(pictures, facet_col=2, wrap=16):
    assert len(pictures.shape) == 3
    pictures = np.moveaxis(pictures, facet_col, 0)
    quilted_img = np.zeros((pictures.shape[0], pictures.shape[1] + 1, pictures.shape[2] + 1))
    quilted_img[:, :-1, :-1] = pictures
    quilted_img = np.reshape(quilted_img, (-1, wrap, *quilted_img.shape[-2:]))
    quilted_img = np.concatenate(tuple(np.concatenate(tuple(quilted_img), axis=1)), axis=1)
    return quilted_img


px.imshow(
    make_quilt((conv1_cycle - conv1_nocycle)[0, :, :, :]),
    color_continuous_scale="RdBu",
    zmin=-100,
    zmax=100,
).show()

# %% Make animation with all the layers


layer_names = ["conv1"] + [f"rconv{i}" for i in range(1, 41)] + ["trunk"]
layers_to_eval = [model_layers[name] for name in layer_names]

layers_cycle = sess.run(layers_to_eval, feed_dict=gs_cycle.feed_dict())
layers_nocycle = sess.run(layers_to_eval, feed_dict=gs_nocycle.feed_dict())


def norm(img):
    return img / np.abs(img).max()


quilts = np.stack([norm(make_quilt((a - b)[0, :, :, :])) for (a, b) in zip(layers_cycle, layers_nocycle)])

zmax = 1.0

px.imshow(
    plt.get_cmap("RdBu")(quilts / 2 + 0.5)[..., :3],
    animation_frame=0,
    color_continuous_scale="RdBu",
    zmin=-zmax,
    zmax=zmax,
    binary_string=True,
).show()


# %% Do the same with the other non-cyclic image


gs_nocycle_prime = sgf_to_gs(SGF.parse_file("../connection_test_position_Bprime.sgf"))

gs_nocycle_prime.feed_dict()[model.bin_inputs]
gs_nocycle.feed_dict()[model.bin_inputs]

# %% Make animation with all the layers

layer_names = ["conv1"] + [f"rconv{i}" for i in range(1, 41)] + ["trunk"]
layers_to_eval = [model_layers[name] for name in layer_names]

layers_nocycle_prime = sess.run(layers_to_eval, feed_dict=gs_nocycle_prime.feed_dict())
layers_nocycle = sess.run(layers_to_eval, feed_dict=gs_nocycle.feed_dict())

quilts = np.stack([norm(make_quilt((a - b)[0, :, :, :])) for (a, b) in zip(layers_nocycle_prime, layers_nocycle)])

zmax = 1.0

px.imshow(
    plt.get_cmap("RdBu")(quilts / 2 + 0.5)[..., :3],
    animation_frame=0,
    color_continuous_scale="RdBu",
    zmin=-zmax,
    zmax=zmax,
    binary_string=True,
).show()

# %% Plot rconv26/conv1a

l_nocycle = sess.run(model_layers["rconv26/conv1a"], feed_dict=gs_nocycle.feed_dict())
l_cycle = sess.run(model_layers["rconv26/conv1a"], feed_dict=gs_cycle.feed_dict())

quilts = make_quilt(np.concatenate([l_nocycle[0], l_cycle[0]], axis=2))

zmax = np.abs(quilts).max()
img = plt.get_cmap("RdBu")(quilts / 2 + 0.5)[..., :3]
px.imshow(
    quilts, color_continuous_scale="RdBu", color_continuous_midpoint=0.0, zmin=-zmax, zmax=zmax, binary_string=False
).show()

# quilts = np.stack([norm(make_quilt((a - b)[0, :, :, :])) for (a, b) in zip(layers_nocycle_prime, layers_nocycle)])

# %% Plot all the activations by themselves

for layers in [layers_cycle, layers_nocycle]:
    quilts = np.stack([norm(make_quilt(a[0, :, :, :])) for a in layers_cycle])

    print(
        px.imshow(
            plt.get_cmap("RdBu")(quilts / 2 + 0.5)[..., :3],
            animation_frame=0,
            color_continuous_scale="RdBu",
            zmin=-zmax,
            zmax=zmax,
            binary_string=True,
        ).show()
    )
