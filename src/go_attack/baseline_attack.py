"""Functions for running baseline attacks against KataGo."""
import random
import re
from pathlib import Path
from subprocess import DEVNULL, PIPE, Popen
from typing import IO, AnyStr, List, Literal, Optional, Tuple

from tqdm import tqdm

from go_attack.adversarial_policy import (
    POLICIES,
    AdversarialPolicy,
    MyopicWhiteBoxPolicy,
    NonmyopicWhiteBoxPolicy,
    PassingWrapper,
)
from go_attack.go import Color, Game, Move
from go_attack.utils import select_best_gpu

PASSING_BEHAVIOR = (
    "standard",
    "avoid-pass-alive-territory",
    "last-resort",
    "last-resort-oracle",
    "only-when-ahead",
    "only-when-behind",
)


def start_engine(
    executable_path: Path,
    config_path: Path,
    model_path: Path,
    num_playouts: int,
    passing_behavior: str,
    gpu: int,
) -> Tuple[IO[AnyStr], IO[AnyStr]]:
    """Starts the KataGo engine, returning a tuple with the engines stdin and stdout."""
    proc = Popen(
        [
            str(executable_path),
            "gtp",
            "-model",
            str(model_path),
            "-override-config",
            ",".join(
                [
                    f"passingBehavior={passing_behavior}",
                    f"maxPlayouts={num_playouts}",
                ],
            ),
            "-config",
            str(config_path),
        ],
        bufsize=0,  # We need to disable buffering to get stdout line-by-line
        env={"CUDA_VISIBLE_DEVICES": str(gpu)},
        stderr=DEVNULL,
        stdin=PIPE,
        stdout=PIPE,
    )
    stdin = proc.stdin
    stdout = proc.stdout
    assert stdin is not None and stdout is not None
    return stdin, stdout


def make_log_dir(
    log_root: Path,
    model_path: Path,
    adversarial_policy: str,
    num_playouts: int,
    passing_behavior: str,
) -> Path:
    """Make a log directory and return the Path to it."""
    desc = f"model={model_path.stem}"
    desc += f"_policy={adversarial_policy}"
    desc += f"_playouts={num_playouts}"
    desc += f"_pass={passing_behavior}"

    log_dir = log_root / desc
    log_dir.mkdir(exist_ok=True, parents=True)
    print(f"Logging SGF game files to '{str(log_dir)}'")
    return log_dir


def run_baseline_attack(
    model_path: Path,
    adversarial_policy: str,
    num_playouts: int,
    passing_behavior: str,
    gpu: Optional[int] = None,
    *,
    board_size: int = 19,
    config_path: Path,
    executable_path: Path,
    log_analysis: bool = False,
    log_root: Optional[Path] = None,
    moves_before_pass: int = 211,
    num_games: int = 1,
    progress_bar: bool = True,
    seed: int = 42,
    verbose: bool = False,
    victim: Literal["B", "W"] = "B",
) -> List[Game]:
    """Run a baseline attack against KataGo."""
    if adversarial_policy not in POLICIES:
        raise ValueError(f"adversarial_policy must be one of {POLICIES}")
    if passing_behavior not in PASSING_BEHAVIOR:
        raise ValueError(f"passing_policy must be one of {PASSING_BEHAVIOR}")
    if not config_path.exists():
        raise ValueError(f"config_path must exist: {config_path}")
    if not model_path.exists():
        raise ValueError(f"model_path must exist: {model_path}")
    if gpu is None:
        gpu = select_best_gpu(10)

    # Start up the KataGo executable.
    to_engine, from_engine = start_engine(
        executable_path,
        config_path,
        model_path,
        num_playouts,
        passing_behavior,
        gpu,
    )

    log_dir = None
    if log_root is not None:
        log_dir = make_log_dir(
            log_root,
            model_path,
            adversarial_policy,
            num_playouts,
            passing_behavior,
        )

    def maybe_print(msg):
        if verbose:
            print(msg)

    def send_msg(msg):
        to_engine.write(f"{msg}\n".encode("ascii"))

    def print_kata_board():
        send_msg("showboard")
        for _ in range(board_size + 3):
            msg = from_engine.readline().decode("ascii").strip()
            print(msg)

    def get_msg(pattern):
        while True:
            msg = from_engine.readline().decode("ascii").strip()
            if msg == "? genmove returned null locati on or illegal move":
                print("Internal KataGo error; board state:")
                print_kata_board()
            elif hit := pattern.fullmatch(msg):
                return hit

    def make_policy() -> AdversarialPolicy:
        if policy_cls in (MyopicWhiteBoxPolicy, NonmyopicWhiteBoxPolicy):
            policy = policy_cls(
                game,
                victim_color.opponent(),
                to_engine,
                from_engine,
            )  # pytype: disable=not-instantiable,wrong-arg-count
        else:
            policy = policy_cls(
                game,
                victim_color.opponent(),
            )  # pytype: disable=not-instantiable
        return PassingWrapper(policy, moves_before_pass)

    send_msg(f"boardsize {board_size}")

    random.seed(seed)
    games = []
    policy_cls = POLICIES[adversarial_policy]
    victim_color = Color.from_str(victim)
    victim_name = "Black" if victim == "B" else "White"

    analysis_regex = re.compile(r"info.*|play pass")
    analysis_move_regex = re.compile(r"play ([A-Z][0-9]{1,2}|pass)")
    move_regex = re.compile(r"= ([A-Z][0-9]{1,2}|pass)")
    score_regex = re.compile(r"= (B|W)\+([0-9]+\.?[0-9]*)|= 0")

    game_iter = range(num_games)
    if not verbose and progress_bar:
        game_iter = tqdm(game_iter, desc="Playing", unit="games")

    for i in game_iter:
        maybe_print(f"\n--- Game {i + 1} of {num_games} ---")
        game = Game(board_size)

        policy = make_policy()

        def take_turn():
            move = policy.next_move()
            game.play_move(move)

            vertex = str(move) if move else "pass"
            send_msg(f"play {victim_color.opponent()} {vertex}")
            maybe_print("Passing" if move is None else f"Playing {vertex}")

        # Play first iff we're black
        if victim_color.opponent() == Color.BLACK:
            take_turn()

        analyses = []  # Only used when --analysis-log-dir is set
        turn = 1
        while not game.is_over():
            # Ask for the analysis as well as the move
            if log_analysis:
                send_msg(f"kata-genmove_analyze {victim}")
                analysis = get_msg(analysis_regex).group(0)

                # Weird special case where the engine returns "play pass"
                # and no actual analysis
                if analysis == "play pass":
                    victim_move = "pass"
                else:
                    analyses.append(analysis)
                    victim_move = get_msg(analysis_move_regex).group(1)
            else:
                send_msg(f"genmove {victim}")
                victim_move = get_msg(move_regex).group(1)

            game.play_move(Move.from_str(victim_move))
            maybe_print(f"\nTurn {turn}")
            maybe_print(f"KataGo played: {victim_move}")

            take_turn()

            turn += 1

        # Save the analysis file if needed
        if log_analysis:
            assert log_dir is not None
            analysis_log_dir = log_dir / "analyses"
            analysis_log_dir.mkdir(exist_ok=True, parents=True)
            with open(analysis_log_dir / f"game_{i}.txt", "w") as f:
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

        if verbose:
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

        games.append(game)
        send_msg("clear_board")

        # Save the game to disk if necessary
        if log_dir:
            strat_title = adversarial_policy.capitalize()
            sgf = game.to_sgf(f"{strat_title} attack; {victim_name} victim")

            with open(log_dir / f"game_{i}.sgf", "w") as f:
                f.write(sgf)

    return games
