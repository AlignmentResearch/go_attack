#!/usr/bin/env python3

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
    go_attack_path = os.path.realpath(os.getcwd())
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


def myshow(self, *args, **kwargs):
    html = pio.to_html(self)
    mhash = hashlib.md5(html.encode("utf-8")).hexdigest()
    if not os.path.isdir(".ob-jupyter"):
        os.mkdir(".ob-jupyter")
    fhtml = os.path.join(".ob-jupyter", mhash + ".html")

    with open(fhtml, "w") as f:
        f.write(html)

    # display(FileLink(fhtml, result_html_suffix=''))
    # return Image(pio.to_image(self, 'png'))
    return FileLink(fhtml, result_html_suffix="")


go.Figure.show = myshow


# %% Load model from saved files

MODEL_DIR = Path("/data/katago-networks/kata1-b40c256-s11840935168-d2898845681/saved_model")
NAME_SCOPE = "swa_model"
POS_LEN = 19  # 19x19 board

with open(MODEL_DIR / "model.config.json", "r") as f:
    model_config = json.load(f)

sess = tf.InteractiveSession()

with tf.variable_scope(NAME_SCOPE):
    model = Model(model_config, POS_LEN, {})

tf.compat.v1.train.Saver().restore(sess, str(MODEL_DIR / "variables" / "variables"))

# Many features of the model
policy0_output = tf.nn.softmax(model.policy_output[:, :, 0])
policy1_output = tf.nn.softmax(model.policy_output[:, :, 1])
value_output = tf.nn.softmax(model.value_output)
scoremean_output = 20.0 * model.miscvalues_output[:, 0]
scorestdev_output = 20.0 * tf.math.softplus(model.miscvalues_output[:, 1])
lead_output = 20.0 * model.miscvalues_output[:, 2]
vtime_output = 40.0 * tf.math.softplus(model.miscvalues_output[:, 3])
estv_output = tf.sqrt(0.25 * tf.math.softplus(model.moremiscvalues_output[:, 0]))
ests_output = tf.sqrt(30.0 * tf.math.softplus(model.moremiscvalues_output[:, 1]))
td_value_output = tf.nn.softmax(model.miscvalues_output[:, 4:7])
td_value_output2 = tf.nn.softmax(model.miscvalues_output[:, 7:10])
td_value_output3 = tf.nn.softmax(model.moremiscvalues_output[:, 2:5])
td_score_output = model.moremiscvalues_output[:, 5:8] * 20.0
vtime_output = 40.0 * tf.math.softplus(model.miscvalues_output[:, 3])
vtime_output = 40.0 * tf.math.softplus(model.miscvalues_output[:, 3])
ownership_output = tf.tanh(model.ownership_output)
scoring_output = model.scoring_output
futurepos_output = tf.tanh(model.futurepos_output)
seki_output = tf.nn.softmax(model.seki_output[:, :, :, 0:3])
seki_output = seki_output[:, :, :, 1] - seki_output[:, :, :, 2]
seki_output2 = tf.sigmoid(model.seki_output[:, :, :, 3])
scorebelief_output = tf.nn.softmax(model.scorebelief_output)
sbscale_output = model.sbscale3_layer

# %% Create board and evaluate it
RULES = {
    "koRule": "KO_POSITIONAL",
    "scoringRule": "SCORING_AREA",
    "taxRule": "TAX_NONE",
    "multiStoneSuicideLegal": True,
    "hasButton": False,
    "encorePhase": 0,
    "passWouldEndPhase": False,
    "whiteKomi": 7.5,
}


class GameState:
    def __init__(self, board_size, board=None, rules=None):
        self.board_size = board_size
        if board is None:
            board = Board(size=board_size)
        self.board = board
        assert self.board_size == self.board.size

        self.moves = []
        self.boards = [self.board.copy()]
        self.rules = rules if rules is not None else RULES

    def copy(self):
        gs = GameState(self.board_size, board=self.board.copy(), rules=self.rules.copy())
        gs.moves = self.moves.copy()
        gs.boards = self.boards.copy()
        return gs

    def feed_dict(self, model=model):
        bin_input_data = np.zeros(shape=[1] + model.bin_input_shape, dtype=np.float32)
        global_input_data = np.zeros(shape=[1] + model.global_input_shape, dtype=np.float32)
        pla = self.board.pla
        opp = Board.get_opp(pla)
        move_idx = len(self.moves)
        model.fill_row_features(
            self.board,
            pla,
            opp,
            self.boards,
            self.moves,
            move_idx,
            RULES,
            bin_input_data,
            global_input_data,
            idx=0,
        )
        feed_dict = {
            model.bin_inputs: bin_input_data,
            model.global_inputs: global_input_data,
            model.symmetries: np.zeros([3], dtype=np.bool),
            model.include_history: np.ones([1, 5], dtype=np.float32),
        }
        return feed_dict

    def play(self, player: int, move_xy: Tuple[int, int]):
        move = self.board.loc(*move_xy)
        self.board.play(player, move)
        self.moves.append((player, move))
        self.boards.append(self.board.copy())

    def board_as_square(self):
        return self.board.board[:-1].reshape((self.board_size + 2, self.board_size + 1))[1:-1, 1:]

    def show(
        self,
        policy: Optional[np.ndarray] = None,
        w: float = 20,
        heatmap_min: Optional[float] = None,
        heatmap_max: Optional[float] = None,
        cmap: Optional[matplotlib.colors.ListedColormap] = None,
    ):
        """Visualize currently GoBoard state with an optional policy heatmap."""
        n = self.board_size
        if cmap is None:
            cmap = plt.get_cmap("viridis")
        extra = []

        def to_xy(cell):
            """Maps a cell (col, row) to an SVG (x, y) coordinate"""
            return w + w * cell[0], w + w * cell[1]

        # Draw the heatmap, if present.
        if policy is not None:
            if policy.shape[:2] == (n, n):
                heatmap = policy
            else:
                heatmap = policy[:-1].reshape((n, n))
            assert heatmap.shape[:2] == (n, n)
            if heatmap_min is None:
                heatmap_min = heatmap.min()
            if heatmap_max is None:
                heatmap_max = heatmap.max() + 1e-20
            assert heatmap_min is not None and heatmap_max is not None
            normalized = (heatmap - heatmap_min) / (heatmap_max - heatmap_min)
            for cell_y in range(n):
                for cell_x in range(n):
                    value = normalized[cell_y, cell_x]
                    x, y = to_xy((cell_x, cell_y))
                    if len(value.shape) == 0:
                        r, g, b, _ = cmap(value)
                    else:
                        r, g, b, *_ = value
                    color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

                    extra.append(
                        f"""
                        <rect
                        x="{x - w/2 - 0.25}" y="{y - w/2 - 0.25}"
                        width="{w + 0.5}" height="{w + 0.5}"
                        style="fill: {color}; stroke: none; opacity: 1.0;"
                        />
                    """
                    )
        # Draw and label the grid.
        for i in range(n):
            extra.append(
                f"""
                <line x1="{w + w * i}" x2="{w + w * i}" y1="{w}" y2="{w * 20 - w}" stroke="black" />
                <line y1="{w + w * i}" y2="{w + w * i}" x1="{w}" x2="{w * 20 - w}" stroke="black" />
                <text x="{w - 15}" y="{w + w * i + 5}" font="bold 2px" style="fill: #ffe7a3; stroke: none;">{str(i)}</text>
                <text x="{w + w * i - 5}" y="{w - 5}" font="bold 2px" style="fill: #ffe7a3; stroke: none;">{str(i)}</text>
            """
            )
        # Draw the star points.
        for i in range(3):
            for j in range(3):
                hoshi = 3 + 6 * i, 3 + 6 * j
                xy = to_xy(hoshi)
                extra.append(
                    f"""
                    <circle cx="{xy[0]}" cy="{xy[1]}" r="4" fill="black" />
                """
                )
        # Render all of the stones on the board.
        for i in range(n):
            for j in range(n):
                xy = to_xy((i, j))
                stone = self.board.board[self.board.loc(i, j)]
                if stone == Board.BLACK:
                    fill = "#000"
                    stroke = "#fff"
                elif stone == Board.WHITE:
                    fill = "#fff"
                    stroke = "#000"
                else:
                    continue
                extra.append(
                    f"""
                    <circle cx="{xy[0]}" cy="{xy[1]}" r="{(w - 2)/2}" style="fill: {fill}; stroke-width: 1; stroke: {stroke};" />
                """
                )

        # Display the SVG.
        content = f"""
        <!-- Board -->
        <rect
            width="{w * 20}" height="{w * 20}"
            rx="{0.75 * w}"
            style="fill: #966f33; stroke-width: 2; stroke: black;"
        />
        {"".join(extra)}
        """
        svg = f"""
        <svg height="{w * 20}" width="{w * 20}" viewBox="-5 -5 {w * 20 + 10} {w * 20 + 10}" version="1.1">
        {content}
        </svg>
        """
        return SVG(svg)

    def get_outputs(self, session=sess, model=model):
        outputs = sess.run(
            [
                policy0_output,
                policy1_output,
                value_output,
                td_value_output,
                td_value_output2,
                td_value_output3,
                scoremean_output,
                td_score_output,
                scorestdev_output,
                lead_output,
                vtime_output,
                estv_output,
                ests_output,
                ownership_output,
                scoring_output,
                futurepos_output,
                seki_output,
                seki_output2,
                scorebelief_output,
                sbscale_output,
            ],
            feed_dict=self.feed_dict(model=model),
        )
        [
            policy0,
            policy1,
            value,
            td_value,
            td_value2,
            td_value3,
            scoremean,
            td_score,
            scorestdev,
            lead,
            vtime,
            estv,
            ests,
            ownership,
            scoring,
            futurepos,
            seki,
            seki2,
            scorebelief,
            sbscale,
        ] = [o[0] for o in outputs]
        board = self.board

        moves_and_probs0 = []
        for i in range(len(policy0)):
            move = model.tensor_pos_to_loc(i, board)
            if i == len(policy0) - 1:
                moves_and_probs0.append((Board.PASS_LOC, policy0[i]))
            elif board.would_be_legal(board.pla, move):
                moves_and_probs0.append((move, policy0[i]))

        moves_and_probs1 = []
        for i in range(len(policy1)):
            move = model.tensor_pos_to_loc(i, board)
            if i == len(policy1) - 1:
                moves_and_probs1.append((Board.PASS_LOC, policy1[i]))
            elif board.would_be_legal(board.pla, move):
                moves_and_probs1.append((move, policy1[i]))

        ownership_flat = ownership.reshape([model.pos_len * model.pos_len])
        ownership_by_loc = []
        board = self.board
        for y in range(board.size):
            for x in range(board.size):
                loc = board.loc(x, y)
                pos = model.loc_to_tensor_pos(loc, board)
                if board.pla == Board.WHITE:
                    ownership_by_loc.append((loc, ownership_flat[pos]))
                else:
                    ownership_by_loc.append((loc, -ownership_flat[pos]))

        scoring_flat = scoring.reshape([model.pos_len * model.pos_len])
        scoring_by_loc = []
        board = self.board
        for y in range(board.size):
            for x in range(board.size):
                loc = board.loc(x, y)
                pos = model.loc_to_tensor_pos(loc, board)
                if board.pla == Board.WHITE:
                    scoring_by_loc.append((loc, scoring_flat[pos]))
                else:
                    scoring_by_loc.append((loc, -scoring_flat[pos]))

        futurepos0_flat = futurepos[:, :, 0].reshape([model.pos_len * model.pos_len])
        futurepos0_by_loc = []
        board = self.board
        for y in range(board.size):
            for x in range(board.size):
                loc = board.loc(x, y)
                pos = model.loc_to_tensor_pos(loc, board)
                if board.pla == Board.WHITE:
                    futurepos0_by_loc.append((loc, futurepos0_flat[pos]))
                else:
                    futurepos0_by_loc.append((loc, -futurepos0_flat[pos]))

        futurepos1_flat = futurepos[:, :, 1].reshape([model.pos_len * model.pos_len])
        futurepos1_by_loc = []
        board = self.board
        for y in range(board.size):
            for x in range(board.size):
                loc = board.loc(x, y)
                pos = model.loc_to_tensor_pos(loc, board)
                if board.pla == Board.WHITE:
                    futurepos1_by_loc.append((loc, futurepos1_flat[pos]))
                else:
                    futurepos1_by_loc.append((loc, -futurepos1_flat[pos]))

        seki_flat = seki.reshape([model.pos_len * model.pos_len])
        seki_by_loc = []
        board = self.board
        for y in range(board.size):
            for x in range(board.size):
                loc = board.loc(x, y)
                pos = model.loc_to_tensor_pos(loc, board)
                if board.pla == Board.WHITE:
                    seki_by_loc.append((loc, seki_flat[pos]))
                else:
                    seki_by_loc.append((loc, -seki_flat[pos]))

        seki_flat2 = seki2.reshape([model.pos_len * model.pos_len])
        seki_by_loc2 = []
        board = self.board
        for y in range(board.size):
            for x in range(board.size):
                loc = board.loc(x, y)
                pos = model.loc_to_tensor_pos(loc, board)
                seki_by_loc2.append((loc, seki_flat2[pos]))

        moves_and_probs = sorted(moves_and_probs0, key=lambda moveandprob: moveandprob[1], reverse=True)
        # Generate a random number biased small and then find the appropriate move to make
        # Interpolate from moving uniformly to choosing from the triangular distribution
        alpha = 1
        beta = 1 + math.sqrt(max(0, len(self.moves) - 20))
        r = np.random.beta(alpha, beta)
        print("r", r)
        probsum = 0.0
        i = 0
        genmove_result = Board.PASS_LOC
        while True:
            (move, prob) = moves_and_probs[i]
            probsum += prob
            print("probsum", probsum)
            if i >= len(moves_and_probs) - 1 or probsum > r:
                genmove_result = move
                break
            i += 1

        return {
            "policy0": policy0,
            "policy1": policy1,
            "moves_and_probs0": moves_and_probs0,
            "moves_and_probs1": moves_and_probs1,
            "value": value,
            "td_value": td_value,
            "td_value2": td_value2,
            "td_value3": td_value3,
            "scoremean": scoremean,
            "td_score": td_score,
            "scorestdev": scorestdev,
            "lead": lead,
            "vtime": vtime,
            "estv": estv,
            "ests": ests,
            "ownership": ownership,
            "ownership_by_loc": ownership_by_loc,
            "scoring": scoring,
            "scoring_by_loc": scoring_by_loc,
            "futurepos": futurepos,
            "futurepos0_by_loc": futurepos0_by_loc,
            "futurepos1_by_loc": futurepos1_by_loc,
            "seki": seki,
            "seki_by_loc": seki_by_loc,
            "seki2": seki2,
            "seki_by_loc2": seki_by_loc2,
            "scorebelief": scorebelief,
            "sbscale": sbscale,
            "genmove_result": genmove_result,
        }


gs = GameState(POS_LEN)

# %% Run the model and plot the activations

policy = sess.run(model.policy_output, feed_dict=gs.feed_dict())
gs.show(policy[0, :, 0])

# %% Check which side is white or black

game = "B[hk];W[ik];B[hj];W[ij];B[om];W[hi];B[lp];W[gj];B[qq];W[gk]".split(";")

gs = GameState(POS_LEN)
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


gs_cycle = sgf_to_gs(SGF.parse_file("connection_test_position_A.sgf"))
gs_nocycle = sgf_to_gs(SGF.parse_file("connection_test_position_B.sgf"))


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


gs_nocycle_prime = sgf_to_gs(SGF.parse_file("connection_test_position_Bprime.sgf"))

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

# %% Plot all the activations by themselves

for layers in [layers_cycle, layers_nocycle, layers_nocycle_prime]:
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
