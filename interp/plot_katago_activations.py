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
from board import Board
from model import Model
import common

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
    def __init__(self, board_size, rules=None):
        self.board_size = board_size
        self.board = Board(size=board_size)
        self.moves = []
        self.boards = [self.board.copy()]
        self.rules = rules if rules is not None else RULES

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
                heatmap = policy[0, :-1, 0].reshape((n, n))
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
                    stroke = "#444"
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


gs = GameState(POS_LEN)

# %% Run the model and plot the activations


policy = sess.run(model.policy_output, feed_dict=gs.feed_dict())
