import random
import re
from argparse import ArgumentParser
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Literal

import sente
from tqdm import tqdm

from go_attack.adversarial_policy import (
    POLICIES,
    MyopicWhiteBoxPolicy,
    NonmyopicWhiteBoxPolicy,
    PassingWrapper,
)
from go_attack.utils import select_best_gpu


def main():
    parser = ArgumentParser(
        description="Run a hardcoded adversarial attack against KataGo"
    )
    parser.add_argument("--config", type=Path, default=None, help="Path to config file")
    parser.add_argument(
        "--executable", type=Path, default=None, help="Path to KataGo executable"
    )
    parser.add_argument("--model", type=Path, default=None, help="model")
    parser.add_argument(
        "-n", "--num-games", type=int, default=100, help="Number of games"
    )
    parser.add_argument(
        "--num-playouts",
        type=int,
        default=512,
        help="Maximum number of MCTS playouts KataGo is allowed to use",
    )
    parser.add_argument(
        "--log-dir", type=Path, default=None, help="Where to save logged games"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--size", type=int, default=19, help="Board size")
    parser.add_argument(
        "--strategy",
        type=str,
        choices=tuple(POLICIES),
        default="edge",
        help="Adversarial policy to use",
    )
    parser.add_argument(
        "--turns-before-pass",
        type=int,
        default=211,  # Avg. game length
        help="Number of turns before accepting a pass from KataGo and ending the game",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Output every move"
    )
    parser.add_argument(
        "--victim",
        type=str,
        choices=("B", "W"),
        default="B",
        help="The player to attack (black or white)",
    )
    args = parser.parse_args()

    # The mirror strategy only makes sense when we're attacking black because we need
    # the victim to play first in order to know where to play next
    if args.strategy == "mirror" and args.victim != "B":
        raise ValueError("Mirror strategy only works when victim == black")

    # Try to find the config file automatically
    config_path = args.config
    if config_path is None:
        config_path = Path("go_attack") / "configs" / "katago" / "baseline_attack.cfg"

    # Try to find the executable automatically
    katago_exe = args.executable
    if katago_exe is None:
        katago_exe = Path("engines") / "KataGo-custom" / "cpp" / "katago"

    # Try to find the model automatically
    if args.model is None:
        root = Path("go_attack") / "models"
        model_path = min(
            root.glob("*.bin.gz"), key=lambda x: x.stat().st_size, default=None
        )
        if model_path is None:
            raise FileNotFoundError("Could not find model; please set the --model flag")
    else:
        model_path = args.model

    print("Running random attack baseline\n")
    print(f"Using KataGo executable at '{str(katago_exe)}'")
    print(f"Using model at '{str(model_path)}'")
    print(f"Using config file at '{str(config_path)}'")

    module_root = Path(__file__).parent.parent
    proc = Popen(
        [
            "docker",
            "run",
            "--gpus",
            f"device={select_best_gpu(10)}",
            "-v",
            f"{module_root}:/go_attack",  # Mount the module root
            "-i",
            "humancompatibleai/goattack:cpp",
            str(katago_exe),
            "gtp",
            "-model",
            str(model_path),
            "-override-config",
            f"maxPlayouts={args.num_playouts}",
            "-config",
            str(config_path),
        ],
        bufsize=0,  # We need to disable buffering to get stdout line-by-line
        stdin=PIPE,
        stderr=PIPE,
        stdout=PIPE,
    )
    stderr = proc.stderr
    stdin = proc.stdin
    stdout = proc.stdout
    assert stderr is not None and stdin is not None and stdout is not None

    # Skip input until we see "GTP ready" message
    print(f"\nWaiting for GTP ready message...")
    while msg := stderr.readline().decode("ascii").strip():
        if msg.startswith("GTP ready"):
            print(f"Engine ready. Starting game.")
            break

    attacker = "B" if args.victim == "W" else "W"
    move_regex = re.compile(r"= ([A-Z][0-9]{1,2}|pass)")
    score_regex = re.compile(r"= (B|W)\+([0-9]+\.?[0-9]*)")

    def get_msg(pattern):
        while True:
            msg = stdout.readline().decode("ascii").strip()
            if hit := pattern.fullmatch(msg):
                return hit

    def maybe_print(msg):
        if args.verbose:
            print(msg)

    def send_msg(msg):
        stdin.write(f"{msg}\n".encode("ascii"))

    # Alphabet without I
    import numpy as np

    np.set_printoptions(linewidth=150)
    letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"[: args.size]
    send_msg(f"boardsize {args.size}\n")
    if args.log_dir:
        args.log_dir.mkdir(exist_ok=True)
        print(f"Logging SGF game files to '{str(args.log_dir)}'")

    game_iter = range(args.num_games)
    if not args.verbose:
        game_iter = tqdm(game_iter, desc="Playing", unit="games")

    random.seed(args.seed)
    policy_cls = POLICIES[args.strategy]
    victim = letter_to_stone(args.victim)
    scores = []

    for i in game_iter:
        maybe_print(f"\n--- Game {i + 1} of {args.num_games} ---")
        game = sente.Game(args.size)

        # Add comment to the SGF file
        strat_title = args.strategy.capitalize()
        victim_title = "Black" if args.victim == "B" else "White"
        game.comment = f"{strat_title} attack; {victim_title} victim"

        if policy_cls in (MyopicWhiteBoxPolicy, NonmyopicWhiteBoxPolicy):
            policy = policy_cls(game, opponent(victim), stdin, stdout)
        else:
            policy = policy_cls(game, opponent(victim))

        policy = PassingWrapper(policy, args.turns_before_pass)

        def take_turn():
            move = policy.next_move()
            try:
                game.play(move)
            # Sometimes happens with ownership policy for some reason
            except sente.exceptions.IllegalMoveException:
                move = None
                game.play(move)

            if move is None:
                send_msg(f"play {attacker} pass\n")
                maybe_print("Passing")
            else:
                vertex = (
                    f"{letters[move.get_x()]}{move.get_y() + 1}" if move else "pass"
                )
                send_msg(f"play {attacker} {vertex}\n")
                maybe_print(f"Playing move {vertex}")

        # Play first iff we're black
        if attacker == "B":
            take_turn()

        stdin.write(f"genmove {args.victim}\n".encode("ascii"))
        turn = 1
        while True:
            hit = get_msg(move_regex)
            victim_move = hit.group(1)

            if victim_move == "resign":
                game.resign()

            if game.is_over():
                stdin.write("final_score\n".encode("ascii"))

                hit = get_msg(score_regex)
                score = float(hit.group(2))
                player = "Black" if hit.group(1) == "B" else "White"

                maybe_print(f"{player} won, up {score} points.")
                maybe_print(game)
                if hit.group(1) != args.victim:
                    score = -score

                scores.append(score)
                stdin.write("clear_board\n".encode("ascii"))

                # Save the game to disk if necessary
                if args.log_dir:
                    sente.sgf.dump(game, str(args.log_dir / f"game_{i}.sgf"))
                break

            if victim_move == "pass":
                game.play(None)
            else:
                letter, num = victim_move[0], int(victim_move[1:])
                victim = sente.stone.BLACK if attacker == "W" else sente.stone.WHITE
                sente_move = sente.Move(letters.find(letter), num - 1, victim)
                game.play(sente_move)

            maybe_print(f"\nTurn {turn}")
            maybe_print(f"KataGo played: {victim_move}")

            take_turn()

            turn += 1
            stdin.write(f"genmove {args.victim}\n".encode("ascii"))

    print(f"\nAverage score: {sum(scores) / len(scores)}")


def opponent(player: sente.stone) -> sente.stone:
    return sente.stone.BLACK if player == sente.stone.WHITE else sente.stone.WHITE


def letter_to_stone(letter: Literal["B", "W"]) -> sente.stone:
    return sente.stone.BLACK if letter == "B" else sente.stone.WHITE


if __name__ == "__main__":
    main()
