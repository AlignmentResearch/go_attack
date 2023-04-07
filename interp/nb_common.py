#!/usr/bin/env python3
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import matplotlib
import matplotlib.colors
import matplotlib.pyplot as plt
import numpy as np
import plotly.io as pio
import tensorflow as tf
from IPython.display import SVG

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

# %% Emacs plotly render


class EmacsRenderer(pio.base_renderers.ColabRenderer):
    save_dir = "ob-jupyter"
    base_url = f"http://localhost:8888/files"

    def to_mimebundle(self, fig_dict):
        html = super().to_mimebundle(fig_dict)["text/html"]

        mhash = hashlib.md5(html.encode("utf-8")).hexdigest()
        if not os.path.isdir(self.save_dir):
            os.mkdir(self.save_dir)
        fhtml = os.path.join(self.save_dir, mhash + ".html")
        with open(fhtml, "w") as f:
            f.write(html)

        return {"text/html": f'<a href="{self.base_url}/{fhtml}">Click to open {fhtml}</a>'}


pio.renderers["emacs"] = EmacsRenderer()


def set_plotly_renderer(renderer="emacs"):
    pio.renderers.default = renderer


# %%  Model loading utils


def load_model(
    sess: tf.Session,
    pos_len: int,
    model_dir="/data/katago-networks/kata1-b40c256-s11840935168-d2898845681/saved_model",
    name_scope="swa_model",
):
    model_dir = Path(model_dir)
    with open(model_dir / "model.config.json", "r") as f:
        model_config = json.load(f)

    with tf.variable_scope(name_scope):
        model = Model(model_config, pos_len, {})

    tf.compat.v1.train.Saver().restore(sess, str(model_dir / "variables" / "variables"))

    # Many features of the model
    #
    seki_output = tf.nn.softmax(model.seki_output[:, :, :, 0:3])
    return model, dict(
        policy0_output=tf.nn.softmax(model.policy_output[:, :, 0]),
        policy1_output=tf.nn.softmax(model.policy_output[:, :, 1]),
        value_output=tf.nn.softmax(model.value_output),
        scoremean_output=20.0 * model.miscvalues_output[:, 0],
        scorestdev_output=20.0 * tf.math.softplus(model.miscvalues_output[:, 1]),
        lead_output=20.0 * model.miscvalues_output[:, 2],
        vtime_output=40.0 * tf.math.softplus(model.miscvalues_output[:, 3]),
        estv_output=tf.sqrt(0.25 * tf.math.softplus(model.moremiscvalues_output[:, 0])),
        ests_output=tf.sqrt(30.0 * tf.math.softplus(model.moremiscvalues_output[:, 1])),
        td_value_output=tf.nn.softmax(model.miscvalues_output[:, 4:7]),
        td_value_output2=tf.nn.softmax(model.miscvalues_output[:, 7:10]),
        td_value_output3=tf.nn.softmax(model.moremiscvalues_output[:, 2:5]),
        td_score_output=model.moremiscvalues_output[:, 5:8] * 20.0,
        ownership_output=tf.tanh(model.ownership_output),
        scoring_output=model.scoring_output,
        futurepos_output=tf.tanh(model.futurepos_output),
        seki_output=seki_output[:, :, :, 1] - seki_output[:, :, :, 2],
        seki_output2=tf.sigmoid(model.seki_output[:, :, :, 3]),
        scorebelief_output=tf.nn.softmax(model.scorebelief_output),
        sbscale_output=model.sbscale3_layer,
    )


# %% GameState
RULES = {
    "koRule": "KO_POSITIONAL",
    "scoringRule": "SCORING_AREA",
    "taxRule": "TAX_NONE",
    "multiStoneSuicideLegal": True,
    "hasButton": False,
    "encorePhase": 0,
    "passWouldEndPhase": False,
    "whiteKomi": 0.5,
}


class GameState:
    def __init__(self, board_size, board=None, rules=None, model=None, model_outputs=None):
        self.board_size = board_size
        if board is None:
            board = Board(size=board_size)
        self.board = board
        assert self.board_size == self.board.size

        self.moves = []
        self.boards = [self.board.copy()]
        self.rules = rules if rules is not None else RULES
        self.model = model
        self.model_outputs = model_outputs

    def copy(self):
        gs = GameState(self.board_size, board=self.board.copy(), rules=self.rules.copy())
        gs.moves = self.moves.copy()
        gs.boards = self.boards.copy()
        return gs

    def feed_dict(self, model=None):
        model = model or self.model
        assert model is not None

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
        cmap: Optional[Union[matplotlib.colors.ListedColormap, matplotlib.colors.Colormap]] = None,
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

    def get_outputs(
        self, sess: tf.Session, model: Optional[Model] = None, model_outputs: Optional[Dict[str, tf.Tensor]] = None
    ):
        model = model or self.model
        assert model is not None

        model_outputs = model_outputs or self.model_outputs
        assert model_outputs is not None

        sess_outs = [
            model_outputs[k]
            for k in [
                "policy0_output",
                "policy1_output",
                "value_output",
                "td_value_output",
                "td_value_output2",
                "td_value_output3",
                "scoremean_output",
                "td_score_output",
                "scorestdev_output",
                "lead_output",
                "vtime_output",
                "estv_output",
                "ests_output",
                "ownership_output",
                "scoring_output",
                "futurepos_output",
                "seki_output",
                "seki_output2",
                "scorebelief_output",
                "sbscale_output",
            ]
        ]

        # comment ######################]
        outputs = sess.run(sess_outs, feed_dict=self.feed_dict(model=model))
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
