"""Run a hardcoded adversarial attack against KataGo."""

import random
import re
from argparse import ArgumentParser
from pathlib import Path
from subprocess import PIPE, Popen

from tqdm import tqdm

from go_attack.adversarial_policy import (
    POLICIES,
    MyopicWhiteBoxPolicy,
    NonmyopicWhiteBoxPolicy,
    PassingWrapper,
)
from go_attack.go import Color, Game, Move
from go_attack.utils import select_best_gpu


def main():  # noqa: D103
    parser = ArgumentParser(
        description="Run a hardcoded adversarial attack against KataGo",
    )
    parser.add_argument(
        "--analysis-log-dir",
        type=Path,
        default=None,
        help="Where to log analysis from KataGo",
    )
    parser.add_argument("--config", type=Path, default=None, help="Path to config file")
    parser.add_argument(
        "--executable",
        type=Path,
        default=None,
        help="Path to KataGo executable",
    )
    parser.add_argument(
        "--passing-behavior",
        choices=(
            "standard",
            "avoid-pass-alive-territory",
            "last-resort",
            "last-resort-oracle",
            "only-when-ahead",
            "only-when-behind",
        ),
        default="standard",
        help="Behavior that KataGo uses when passing",
        type=str,
    )
    parser.add_argument("--model", type=Path, default=None, help="model")
    parser.add_argument(
        "-n",
        "--num-games",
        type=int,
        default=100,
        help="Number of games",
    )
    parser.add_argument(
        "--num-playouts",
        type=int,
        default=512,
        help="Maximum number of MCTS playouts KataGo is allowed to use",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Where to save logged games",
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
        "--moves-before-pass",
        type=int,
        default=211,  # Avg. game length
        help="Number of moves before accepting a pass from KataGo and ending the game",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Output every move",
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
            root.glob("*.bin.gz"),
            key=lambda x: x.stat().st_size,
            default=None,
        )
        if model_path is None:
            raise FileNotFoundError("Could not find model; please set the --model flag")
    else:
        model_path = args.model
        assert model_path.exists()

    print(f"Running {args.strategy} attack baseline\n")
    print(f"Using KataGo executable at '{str(katago_exe)}'")
    print(f"Using model at '{str(model_path)}'")
    print(f"Using config file at '{str(config_path)}'")

    attacker_letter = "B" if args.victim == "W" else "W"
    victim_name = "Black" if args.victim == "B" else "White"

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
            ",".join(
                [
                    f"passingBehavior={args.passing_behavior}",
                    f"maxPlayouts={args.num_playouts}",
                ]
            ),
            "-config",
            str(config_path),
        ],
        bufsize=0,  # We need to disable buffering to get stdout line-by-line
        stdin=PIPE,
        stderr=open("stderr3.txt", "w"),
        stdout=PIPE,
    )
    stdin = proc.stdin
    stdout = proc.stdout
    assert stdin is not None and stdout is not None

    analysis_regex = re.compile(r"info.*|play pass")
    analysis_move_regex = re.compile(r"play ([A-Z][0-9]{1,2}|pass)")
    move_regex = re.compile(r"= ([A-Z][0-9]{1,2}|pass)")
    score_regex = re.compile(r"= (B|W)\+([0-9]+\.?[0-9]*)|= 0")

    def get_msg(pattern):
        while True:
            msg = stdout.readline().decode("ascii").strip()
            if msg == "? genmove returned null locati on or illegal move":
                print("Internal KataGo error; board state:")
                print_kata_board()
            elif hit := pattern.fullmatch(msg):
                return hit

    def maybe_print(msg):
        if args.verbose:
            print(msg)

    def send_msg(msg):
        stdin.write(f"{msg}\n".encode("ascii"))

    send_msg(f"boardsize {args.size}")
    if args.log_dir:
        args.log_dir.mkdir(exist_ok=True)
        print(f"Logging SGF game files to '{str(args.log_dir)}'")

    game_iter = range(args.num_games)
    if not args.verbose:
        game_iter = tqdm(game_iter, desc="Playing", unit="games")

    random.seed(args.seed)
    policy_cls = POLICIES[args.strategy]
    victim = Color.from_str(args.victim)
    scores = []

    for i in game_iter:
        maybe_print(f"\n--- Game {i + 1} of {args.num_games} ---")
        game = Game(args.size)

        # Add comment to the SGF file
        strat_title = args.strategy.capitalize()

        if policy_cls in (MyopicWhiteBoxPolicy, NonmyopicWhiteBoxPolicy):
            policy = policy_cls(game, victim.opponent(), stdin, stdout)  # type: ignore
        else:
            policy = policy_cls(game, victim.opponent())  # type: ignore

        policy = PassingWrapper(policy, args.moves_before_pass)

        def take_turn():
            move = policy.next_move()
            game.play_move(move)

            vertex = str(move) if move else "pass"
            send_msg(f"play {attacker_letter} {vertex}")
            maybe_print("Passing" if move is None else f"Playing {vertex}")

        def print_kata_board():
            send_msg("showboard")
            for i in range(args.size + 3):
                msg = stdout.readline().decode("ascii").strip()
                print(msg)

        # Play first iff we're black
        if attacker_letter == "B":
            take_turn()

        analyses = []  # Only used when --analysis-log-dir is set
        turn = 1
        while not game.is_over():
            # Ask for the analysis as well as the move
            if args.analysis_log_dir:
                send_msg(f"kata-genmove_analyze {args.victim}")
                analysis = get_msg(analysis_regex).group(0)

                # Weird special case where the engine returns "play pass"
                # and no actual analysis
                if analysis == "play pass":
                    victim_move = "pass"
                else:
                    analyses.append(analysis)
                    victim_move = get_msg(analysis_move_regex).group(1)
            else:
                send_msg(f"genmove {args.victim}")
                victim_move = get_msg(move_regex).group(1)

            game.play_move(Move.from_str(victim_move))
            maybe_print(f"\nTurn {turn}")
            maybe_print(f"KataGo played: {victim_move}")

            take_turn()

            turn += 1

        # Save the analysis file if needed
        if args.analysis_log_dir:
            args.analysis_log_dir.mkdir(exist_ok=True)
            with open(args.analysis_log_dir / f"game_{i}.txt", "w") as f:
                f.write("\n\n".join(analyses))

        # Get KataGo's opinion on the score
        send_msg("final_score")
        hit = get_msg(score_regex)
        if hit.group(0) == "= 0":  # Tie
            kata_margin = 0.0
        else:
            kata_margin = float(hit.group(2))
            if hit.group(1) == "B":
                kata_margin *= -1

        if args.verbose:
            print_kata_board()

        # What do we think about the score?
        black_score, white_score = game.score()
        our_margin = white_score - black_score
        if our_margin > 0:
            maybe_print(f"White won, up {our_margin} points.")
        elif our_margin < 0:
            maybe_print(f"Black won, up {our_margin} points.")
        else:
            maybe_print("Tie")

        # if our_margin != kata_margin:
        #     print(f"KataGo's margin {kata_margin} doesn't match ours {our_margin}!")
        #
        #     print(game)
        #     raise RuntimeError("KataGo's margin doesn't match ours!")

        scores.append(our_margin)
        send_msg("clear_board")

        # Save the game to disk if necessary
        if args.log_dir:
            sgf = game.to_sgf(f"{strat_title} attack; {victim_name} victim")

            with open(args.log_dir / f"game_{i}.sgf", "w") as f:
                f.write(sgf)

    print(f"\nAverage score: {sum(scores) / len(scores)}")


if __name__ == "__main__":
    main()
