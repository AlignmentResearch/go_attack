import argparse
import collections
import json
import math
import os
import sys
import subprocess
import time
import tempfile
from pathlib import Path
from threading import Thread

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import sgfmill
import sgfmill.sgf
import sgfmill.boards
import sgfmill.ascii_boards

BASE_CONFIG = """
logDir = analysis_logs
reportAnalysisWinratesAs = SIDETOMOVE
numAnalysisThreads = 1
nnMaxBatchSize = 16
nnCacheSizePowerOfTwo = 18
nnMutexPoolSizePowerOfTwo = 15
nnRandomize = true
rootNumSymmetriesToSample = 8
"""


def sgfmill_to_str(coord):
    if coord is None or coord == "pass":
        return "pass"
    (y, x) = coord
    return "ABCDEFGHJKLMNOPQRSTUVWXYZ"[x] + str(y + 1)


class KataGo:
    def __init__(
        self,
        name,
        katago_path,
        config_paths,
        model_path,
        override_config,
        override_komi,
        rules,
    ):
        self.name = name
        self.query_counter = 0
        self.override_komi = override_komi
        self.rules = rules

        command = [
            katago_path,
            "analysis",
            "-model",
            model_path,
        ]
        for config in config_paths:
            command += ["-config", str(config)]
        if override_config is not None:
            command += ["-override-config", override_config]
        katago = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.katago = katago

        def printforever():
            while katago.poll() is None:
                data = katago.stderr.readline()
                time.sleep(0)
                if data:
                    print("KataGo: ", data.decode(), end="")
            data = katago.stderr.read()
            if data:
                print("KataGo: ", data.decode(), end="")

        self.stderrthread = Thread(target=printforever)
        self.stderrthread.start()

    def close(self):
        self.katago.stdin.close()

    def query(self, initial_board, moves, komi, max_visits=None):
        query = {}

        query["id"] = str(self.query_counter)
        self.query_counter += 1

        query["moves"] = moves
        query["initialStones"] = []
        for y in range(initial_board.side):
            for x in range(initial_board.side):
                color = initial_board.get(y, x)
                if color:
                    query["initialStones"].append((color, sgfmill_to_str((y, x))))
        query["rules"] = self.rules
        query["komi"] = komi if self.override_komi is None else self.override_komi
        query["boardXSize"] = initial_board.side
        query["boardYSize"] = initial_board.side
        query["includePolicy"] = True
        if max_visits is not None:
            query["maxVisits"] = max_visits

        self.katago.stdin.write((json.dumps(query) + "\n").encode())
        self.katago.stdin.flush()

        # print(json.dumps(query))

        line = ""
        while line == "":
            if self.katago.poll():
                time.sleep(1)
                raise Exception("Unexpected katago exit")
            line = self.katago.stdout.readline()
            line = line.decode().strip()
            # print("Got: " + line)
        response = json.loads(line)

        # print(response)
        return response


def process_sgf_file(filename, func):
    with open(filename, "r") as f:
        game = sgfmill.sgf.Sgf_game.from_string(f.read())
        size = game.get_size()
        board = sgfmill.boards.Board(size)
        moves_since_setup = []
        komi = game.get_komi()
        walk_game_tree(
            filename,
            game.get_root(),
            board.copy(),
            board.copy(),
            moves_since_setup,
            komi,
            func,
        )


def walk_game_tree(
    filename, node, board_at_setup, board, moves_since_setup, komi, func
):
    board = board.copy()
    ab, aw, ae = node.get_setup_stones()
    if ab or aw or ae:
        is_legal = board.apply_setup(ab, aw, ae)
        assert is_legal
        board_at_setup = board.copy()
        moves_since_setup = []
    color, raw = node.get_raw_move()
    if color:
        move = sgfmill.sgf_properties.interpret_go_point(raw, board.side)
        if move:
            (row, col) = move
            try:
                board.play(row, col, color)
            except ValueError:
                print(sgfmill.ascii_boards.render_board(board))
                print(raw, move, color)
                raise ValueError()
        moves_since_setup = moves_since_setup + [(color, sgfmill_to_str(move))]

    if node.has_property("C"):
        if node.find_property("C").strip() == "START":
            correct_moves = []
            wrong_moves = []
            target_winner = None
            for child in node:
                if (
                    child.has_property("C")
                    and child.find_property("C").strip() == "CORRECT"
                ):
                    childcolor, childraw = child.get_raw_move()
                    childmove = sgfmill.sgf_properties.interpret_go_point(
                        childraw, board.side
                    )
                    correct_moves.append((childcolor, childmove))
                if (
                    child.has_property("C")
                    and child.find_property("C").strip() == "WRONG"
                ):
                    childcolor, childraw = child.get_raw_move()
                    childmove = sgfmill.sgf_properties.interpret_go_point(
                        childraw, board.side
                    )
                    wrong_moves.append((childcolor, childmove))

            func(
                filename,
                board_at_setup,
                moves_since_setup,
                komi,
                correct_moves,
                wrong_moves,
                target_winner,
            )
        elif node.find_property("C").strip() == "BLACKWIN":
            target_winner = "b"
            func(
                filename, board_at_setup, moves_since_setup, komi, [], [], target_winner
            )
        elif node.find_property("C").strip() == "WHITEWIN":
            target_winner = "w"
            func(
                filename, board_at_setup, moves_since_setup, komi, [], [], target_winner
            )

    for child in node:
        walk_game_tree(
            filename, child, board_at_setup, board, moves_since_setup, komi, func
        )


def main(temp_config_file):
    """Runs the script.

    Args:
        temp_config_file: A writable temporary file for storing the KataGo config.
    """

    parser = argparse.ArgumentParser(
        description="Evaluates and plots models correctness on cyclic-group situations."
    )
    parser.add_argument(
        "--config",
        help="KataGo config",
        type=Path,
        nargs="+",
        default=[],
    )
    parser.add_argument(
        "--executable",
        help="Path to KataGo executable",
        type=Path,
        default="/engines/KataGo-custom/cpp/katago",
    )
    parser.add_argument(
        "--model",
        help="Path to model or models directory",
        type=Path,
        required=True,
        nargs="+",
    )
    parser.add_argument(
        "--output-dir",
        help="Path to directory at which to output results",
        type=Path,
        default="generated_plots",
    )
    parser.add_argument(
        "--output-scores",
        help="Only output a correctness summary score rather than plots",
        action="store_true",
    )
    parser.add_argument(
        "--override-config",
        help="Extra KataGo config params",
        type=str,
        default="",
    )
    parser.add_argument(
        "--override-komi",
        help=(
            "Value with which to override the games' komi. This argument may "
            "be useful when evaluating a model that was only trained on one "
            "komi, but there is no guarantee that the games still make sense "
            "when their komis are changed."
        ),
        type=float,
    )
    parser.add_argument(
        "--rules",
        help=(
            "Go rules to use. The original script used Chinese rules. There is "
            "no guarantee the games still make sense with other rules."
        ),
        type=str,
        default="Chinese",
    )
    parser.add_argument(
        "--visits",
        help="Number of visits to use for search",
        type=int,
        default=1600,
    )
    args = parser.parse_args()

    output_path = args.output_dir
    os.makedirs(output_path, exist_ok=True)
    sgfs_path = Path(__file__).parent / "sgfs"
    models = []
    for path in args.model:
        if not path.exists():
            raise ValueError(f"File does not exist: {path}")
        if path.is_file():
            models.append(path)
            continue
        for model_path in path.iterdir():
            models.append(model_path)
    models = [(str(path), path.name) for path in models]
    for _, model_name in models:
        print(f"Model: {model_name}")

    temp_config_file.write(BASE_CONFIG)
    temp_config_file.flush()
    configs = [Path(temp_config_file.name)] + args.config
    if len(args.override_config) > 0:
        args.override_config += ","
    args.override_config += f"logToStdout=false,maxVisits0={args.visits}"

    katagos = []
    for model_path, model_name in models:
        katagos.append(
            KataGo(
                model_name,
                args.executable,
                configs,
                model_path,
                args.override_config,
                args.override_komi,
                args.rules,
            )
        )

    def get_policy_and_search_mass(board_at_setup, response, moves):
        policy_mass = 0.0
        weight_total = 0.0
        weight_sum = 0.0

        for move_info in response["moveInfos"]:
            weight_total += move_info["weight"]

        for _, coord in moves:
            if coord is None:
                pos = board_at_setup.side * board_at_setup.side  # pass
            else:
                (y, x) = coord
                pos = x + board_at_setup.side * (board_at_setup.side - 1 - y)
            policy_mass += response["policy"][pos]
            for move_info in response["moveInfos"]:
                if move_info["move"] == sgfmill_to_str(coord):
                    weight_sum += move_info["weight"]

        weight_prop = weight_sum / (1e-30 + weight_total)
        return (policy_mass, weight_prop)

    correct_policy_masses = collections.defaultdict(dict)
    correct_search_masses = collections.defaultdict(dict)
    raw_winrate = collections.defaultdict(dict)
    search_winrate = collections.defaultdict(dict)

    def process(
        filename,
        board_at_setup,
        moves_since_setup,
        komi,
        correct_moves,
        wrong_moves,
        target_winner,
    ):
        for katago in katagos:
            response = katago.query(board_at_setup, moves_since_setup, komi)
            player = (
                "b"
                if len(moves_since_setup) == 0
                or moves_since_setup[-1][0] == "w"
                or moves_since_setup[-1][0] == "W"
                else "w"
            )

            modelname = os.path.basename(filename)
            if len(correct_moves) > 0:
                assert target_winner is None
                assert len(wrong_moves) == 0

                correct_policy_mass, correct_search_mass = get_policy_and_search_mass(
                    board_at_setup, response, correct_moves
                )
                # print(correct_policy_mass, correct_search_mass)
                correct_policy_masses[modelname][katago.name] = correct_policy_mass
                correct_search_masses[modelname][katago.name] = correct_search_mass

            if len(wrong_moves) > 0:
                assert target_winner is None
                assert len(correct_moves) == 0

                wrong_policy_mass, wrong_search_mass = get_policy_and_search_mass(
                    board_at_setup, response, wrong_moves
                )
                # print(wrong_policy_mass, wrong_search_mass)
                correct_policy_masses[modelname][katago.name] = 1.0 - wrong_policy_mass
                correct_search_masses[modelname][katago.name] = 1.0 - wrong_search_mass

            if target_winner is not None:
                assert len(correct_moves) == 0
                assert len(wrong_moves) == 0

            search_winrate[modelname][katago.name] = response["rootInfo"]["winrate"]

            response = katago.query(
                board_at_setup, moves_since_setup, komi, max_visits=1
            )
            raw_winrate[modelname][katago.name] = response["rootInfo"]["winrate"]

    series_names = []
    for sgf_file in os.listdir(sgfs_path):
        print(sgf_file, flush=True)
        process_sgf_file(f"{sgfs_path}/{sgf_file}", process)
        series_names.append(sgf_file)

    if args.output_scores:
        with open(output_path / "cycle_scores.txt", "w") as f:
            for data, label in [
                (correct_policy_masses, "raw policy"),
                (correct_search_masses, f"visits={args.visits}"),
            ]:
                scores = collections.defaultdict(list)
                for sgf, sgf_scores in data.items():
                    for model, score in sgf_scores.items():
                        scores[model].append(score)

                for model, model_scores in scores.items():
                    average_score = sum(model_scores) / len(model_scores)
                    f.write(f"{model} {label} score: {average_score}\n")

        print("Done")
        for katago in katagos:
            katago.close()
        return

    def plot_policy(plotfilename, ylabel, series_names, data):
        data = {
            series_name: data[series_name]
            for series_name in sorted(data.keys())
            if series_name in series_names
        }
        model_names = [model_name for model_path, model_name in models]

        colors = sns.color_palette("husl", n_colors=len(series_names))

        fig, ax = plt.subplots(figsize=(12.5, 8.2))
        for (series_name, series_data), color in zip(data.items(), colors):
            policy_values = [series_data[model_name] for model_name in model_names]
            ax.plot(
                model_names, policy_values, label=series_name, color=color, marker="o"
            )

        ax.legend()
        ax.set_xticklabels(model_names)

        ax.set_xlabel("Model")
        ax.set_ylabel(ylabel)

        ax.set_yscale("symlog", linthresh=1e-3, linscale=(1.0 / math.log(10)))
        ax.set_ylim([0, 1])
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda y, _: "%.3g%%" % (y * 100.0))
        )

        for model_name in model_names:
            ax.axvline(x=model_name, linestyle="-", color="lightgray", alpha=0.5)
        for y in [0.001, 0.01, 0.1, 1.0]:
            ax.axhline(y=y, linestyle="-", color="lightgray", alpha=0.5)
        for y in [y * 0.0001 for y in range(1, 10)]:
            ax.axhline(y=y, linestyle="-", color="lightgray", alpha=0.2)
        for y in [y * 0.001 for y in range(2, 10)]:
            ax.axhline(y=y, linestyle="-", color="lightgray", alpha=0.2)
        for y in [y * 0.01 for y in range(2, 10)]:
            ax.axhline(y=y, linestyle="-", color="lightgray", alpha=0.2)
        for y in [y * 0.1 for y in range(2, 10)]:
            ax.axhline(y=y, linestyle="-", color="lightgray", alpha=0.2)

        # plt.show()
        # plt.figure()
        fig.savefig(plotfilename, dpi=90)

    def plot_winrate(plotfilename, ylabel, series_names, data):
        data = {
            series_name: data[series_name]
            for series_name in sorted(data.keys())
            if series_name in series_names
        }
        model_names = [model_name for model_path, model_name in models]

        colors = sns.color_palette("husl", n_colors=len(series_names))

        power = 2.0

        def ytoplot(y):
            z = 2.0 * (y - 0.5)
            return 0.5 * math.copysign(1.0, z) * (abs(z) ** power) + 0.5

        def plottoy(p):
            z = 2.0 * (y - 0.5)
            return 0.5 * (math.copysign(1.0, z) * (abs(z) ** (1.0 / power))) + 0.5

        fig, ax = plt.subplots(figsize=(12.5, 8.2))
        for (series_name, series_data), color in zip(data.items(), colors):
            winrate_values = [
                ytoplot(series_data[model_name]) for model_name in model_names
            ]
            ax.plot(
                model_names, winrate_values, label=series_name, color=color, marker="o"
            )

        ax.legend()
        ax.set_xticklabels(model_names)

        ax.set_xlabel("Model")
        ax.set_ylabel(ylabel)

        ax.set_ylim([0, 1])

        # ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda ploty, _: "%.3g%%" % (plottoyy*100.0)))

        yticks = [
            (0.01, "1%"),
            (0.02, "2%"),
            (0.03, "3%"),
            (0.05, "5%"),
            (0.07, "7%"),
            (0.10, "10%"),
            (0.15, "15%"),
            (0.20, "20%"),
            (0.30, "30%"),
            (0.50, "50%"),
            (0.70, "70%"),
            (0.80, "80%"),
            (0.85, "85%"),
            (0.90, "90%"),
            (0.93, "93%"),
            (0.95, "95%"),
            (0.97, "97%"),
            (0.98, "98%"),
            (0.99, "99%"),
        ]
        ax.set_yticks(
            [ytoplot(tick[0]) for tick in yticks], [tick[1] for tick in yticks]
        )

        for model_name in model_names:
            ax.axvline(x=model_name, linestyle="-", color="lightgray", alpha=0.5)
        for y, _label in yticks:
            ax.axhline(y=ytoplot(y), linestyle="-", color="lightgray", alpha=0.5)

        # plt.show()
        # plt.figure()
        fig.savefig(plotfilename, dpi=90)

    race_series_names = [
        key for key in series_names if key.startswith("race") and "already" not in key
    ]
    plot_policy(
        os.path.join(output_path, "race-raw.png"),
        "Correct Raw Policy",
        race_series_names,
        correct_policy_masses,
    )
    plot_policy(
        os.path.join(output_path, "race-search.png"),
        "Correct Search Mass",
        race_series_names,
        correct_search_masses,
    )
    plot_winrate(
        os.path.join(output_path, "race-rawwinrate.png"),
        "Raw Winrate",
        race_series_names,
        raw_winrate,
    )
    plot_winrate(
        os.path.join(output_path, "race-searchwinrate.png"),
        "Search Winrate",
        race_series_names,
        search_winrate,
    )

    # raceeye_series_names = [key for key in series_names if key.startswith("raceeye") and "already" not in key]
    # plot_policy(os.path.join(output_path,"raceeye-raw.png"), "Correct Raw Policy", raceeye_series_names, correct_policy_masses)
    # plot_policy(os.path.join(output_path,"raceeye-search.png"), "Correct Search Mass", raceeye_series_names, correct_search_masses)
    # plot_winrate(os.path.join(output_path,"raceeye-rawwinrate.png"), "Raw Winrate", raceeye_series_names, raw_winrate)
    # plot_winrate(os.path.join(output_path,"raceeye-searchwinrate.png"), "Search Winrate", raceeye_series_names, search_winrate)

    racealready_series_names = [
        key for key in series_names if key.startswith("race") and "already" in key
    ]
    plot_policy(
        os.path.join(output_path, "racealready-raw.png"),
        "Non-Wrong Raw Policy",
        racealready_series_names,
        correct_policy_masses,
    )
    plot_policy(
        os.path.join(output_path, "racealready-search.png"),
        "Non-Wrong Search Mass",
        racealready_series_names,
        correct_search_masses,
    )
    plot_winrate(
        os.path.join(output_path, "racealready-rawwinrate.png"),
        "Raw Winrate",
        racealready_series_names,
        raw_winrate,
    )
    plot_winrate(
        os.path.join(output_path, "racealready-searchwinrate.png"),
        "Search Winrate",
        racealready_series_names,
        search_winrate,
    )

    escape_series_names = [key for key in series_names if key.startswith("escape")]
    plot_policy(
        os.path.join(output_path, "escape-raw.png"),
        "Correct Raw Policy",
        escape_series_names,
        correct_policy_masses,
    )
    plot_policy(
        os.path.join(output_path, "escape-search.png"),
        "Correct Search Mass",
        escape_series_names,
        correct_search_masses,
    )
    plot_winrate(
        os.path.join(output_path, "escape-rawwinrate.png"),
        "Raw Winrate",
        escape_series_names,
        raw_winrate,
    )
    plot_winrate(
        os.path.join(output_path, "escape-searchwinrate.png"),
        "Search Winrate",
        escape_series_names,
        search_winrate,
    )

    # escapeeye_series_names = [key for key in series_names if key.startswith("escapeeye") and "eye" in key]
    # plot_policy(os.path.join(output_path,"escapeeye-raw.png"), "Correct Raw Policy", escapeeye_series_names, correct_policy_masses)
    # plot_policy(os.path.join(output_path,"escapeeye-search.png"), "Correct Search Mass", escapeeye_series_names, correct_search_masses)
    # plot_winrate(os.path.join(output_path,"escapeeye-rawwinrate.png"), "Raw Winrate", escapeeye_series_names, raw_winrate)
    # plot_winrate(os.path.join(output_path,"escapeeye-searchwinrate.png"), "Search Winrate", escapeeye_series_names, search_winrate)

    distraction_series_names = [
        key for key in series_names if key.startswith("distraction")
    ]
    plot_policy(
        os.path.join(output_path, "distraction-raw.png"),
        "Correct Raw Policy",
        distraction_series_names,
        correct_policy_masses,
    )
    plot_policy(
        os.path.join(output_path, "distraction-search.png"),
        "Correct Search Mass",
        distraction_series_names,
        correct_search_masses,
    )
    plot_winrate(
        os.path.join(output_path, "distraction-rawwinrate.png"),
        "Raw Winrate",
        distraction_series_names,
        raw_winrate,
    )
    plot_winrate(
        os.path.join(output_path, "distraction-searchwinrate.png"),
        "Search Winrate",
        distraction_series_names,
        search_winrate,
    )

    # distractioneye_series_names = [key for key in series_names if key.startswith("distractioneye") and "eye" in key]
    # plot_policy(os.path.join(output_path,"distractioneye-raw.png"), "Correct Raw Policy", distractioneye_series_names, correct_policy_masses)
    # plot_policy(os.path.join(output_path,"distractioneye-search.png"), "Correct Search Mass", distractioneye_series_names, correct_search_masses)
    # plot_winrate(os.path.join(output_path,"distractioneye-rawwinrate.png"), "Raw Winrate", distractioneye_series_names, raw_winrate)
    # plot_winrate(os.path.join(output_path,"distractioneye-searchwinrate.png"), "Search Winrate", distractioneye_series_names, search_winrate)

    eyelive_series_names = [
        key for key in series_names if key.startswith("eye") and "live" in key
    ]
    plot_policy(
        os.path.join(output_path, "eyelive-raw.png"),
        "Correct Raw Policy",
        eyelive_series_names,
        correct_policy_masses,
    )
    plot_policy(
        os.path.join(output_path, "eyelive-search.png"),
        "Correct Search Mass",
        eyelive_series_names,
        correct_search_masses,
    )
    plot_winrate(
        os.path.join(output_path, "eyelive-rawwinrate.png"),
        "Raw Winrate",
        eyelive_series_names,
        raw_winrate,
    )
    plot_winrate(
        os.path.join(output_path, "eyelive-searchwinrate.png"),
        "Search Winrate",
        eyelive_series_names,
        search_winrate,
    )

    eyekill_series_names = [
        key for key in series_names if key.startswith("eye") and "kill" in key
    ]
    plot_policy(
        os.path.join(output_path, "eyekill-raw.png"),
        "Correct Raw Policy",
        eyekill_series_names,
        correct_policy_masses,
    )
    plot_policy(
        os.path.join(output_path, "eyekill-search.png"),
        "Correct Search Mass",
        eyekill_series_names,
        correct_search_masses,
    )
    plot_winrate(
        os.path.join(output_path, "eyekill-rawwinrate.png"),
        "Raw Winrate",
        eyekill_series_names,
        raw_winrate,
    )
    plot_winrate(
        os.path.join(output_path, "eyekill-searchwinrate.png"),
        "Search Winrate",
        eyekill_series_names,
        search_winrate,
    )

    inevitable_series_names = [
        key for key in series_names if key.startswith("inevitable")
    ]
    plot_winrate(
        os.path.join(output_path, "inevitable-rawwinrate.png"),
        "Raw Winrate",
        inevitable_series_names,
        raw_winrate,
    )
    plot_winrate(
        os.path.join(output_path, "inevitable-searchwinrate.png"),
        "Search Winrate",
        inevitable_series_names,
        search_winrate,
    )

    statusdead_series_names = [
        key for key in series_names if key.startswith("statusdead")
    ]
    plot_winrate(
        os.path.join(output_path, "statusdead-rawwinrate.png"),
        "Raw Winrate",
        statusdead_series_names,
        raw_winrate,
    )
    plot_winrate(
        os.path.join(output_path, "statusdead-searchwinrate.png"),
        "Search Winrate",
        statusdead_series_names,
        search_winrate,
    )

    statusalive_series_names = [
        key for key in series_names if key.startswith("statusalive")
    ]
    plot_winrate(
        os.path.join(output_path, "statusalive-rawwinrate.png"),
        "Raw Winrate",
        statusalive_series_names,
        raw_winrate,
    )
    plot_winrate(
        os.path.join(output_path, "statusalive-searchwinrate.png"),
        "Search Winrate",
        statusalive_series_names,
        search_winrate,
    )

    print("Done")
    for katago in katagos:
        katago.close()


if __name__ == "__main__":
    with tempfile.NamedTemporaryFile("w") as f:
        main(temp_config_file=f)
