"""Functions for running baseline attacks against KataGo."""
import random
import re
from pathlib import Path
from subprocess import PIPE, Popen
from typing import IO, AnyStr, Literal, Optional, Sequence, Tuple, cast

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


def send_msg(to_engine: IO[AnyStr], msg: str) -> None:
    """Sends message `msg` to game engine `to_engine`."""
    to_engine.write(f"{msg}\n".encode("ascii"))


def start_engine(
    executable_path: Path,
    config_path: Path,
    model_path: Path,
    num_playouts: int,
    passing_behavior: str,
    gpu: int,
    verbose: bool,
) -> Tuple[IO[bytes], IO[bytes]]:
    """Starts the KataGo engine, returning a tuple with the engines stdin and stdout."""
    args = [
        str(executable_path),
        "gtp",
        "-model",
        str(model_path),
        "-override-config",
        f"passingBehavior={passing_behavior},maxPlayouts={num_playouts}",
        "-config",
        str(config_path),
    ]
    if verbose:
        print(f"Starting engine with args: {args}")

    proc = Popen(
        args,
        bufsize=0,  # We need to disable buffering to get stdout line-by-line
        env={"CUDA_VISIBLE_DEVICES": str(gpu)},
        stderr=open("/tmp/go-baseline-attack.stderr", "w"),
        stdin=PIPE,
        stdout=PIPE,
    )
    to_engine = proc.stdin
    from_engine = proc.stdout
    assert to_engine is not None and from_engine is not None
    return to_engine, from_engine


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


def rollout_policy(
    game: Game,
    policy: AdversarialPolicy,
    victim_color: Color,
    from_engine: IO[AnyStr],
    to_engine: IO[AnyStr],
    log_analysis: bool,
    verbose: bool,
) -> Tuple[Game, Sequence[str]]:
    """Rollouts `policy` against engine with pipe `from_engine`."""

    def maybe_print(msg):
        if verbose:
            print(msg)

    def print_kata_board():
        send_msg(to_engine, "showboard")
        for _ in range(game.board_size + 3):
            msg = from_engine.readline().decode("ascii").strip()
            print(msg)

    def get_msg(pattern: re.Pattern) -> re.Match:
        while True:
            msg = from_engine.readline().decode("ascii").strip()
            if hit := pattern.fullmatch(msg):
                return hit

    def take_turn():
        move = policy.next_move()
        game.play_move(move)

        vertex = str(move) if move else "pass"
        send_msg(to_engine, f"play {victim_color.opponent()} {vertex}")
        maybe_print("Passing" if move is None else f"Playing {vertex}")

    # Play first iff we're black
    if victim_color.opponent() == Color.BLACK:
        take_turn()

    analyses = []  # Only used when --analysis-log-dir is set
    turn = 1
    while not game.is_over():
        if log_analysis:
            # Ask for the analysis as well as the move
            send_msg(to_engine, f"kata-genmove_analyze {victim_color}")
            analysis_regex = re.compile(r"info.*|play pass")

            # For some reason pytype thinks this is `bytes` but it's definitely `str`;
            # see https://docs.python.org/3/library/re.html?highlight=re#re.Match.group
            analysis = cast(str, get_msg(analysis_regex).group(0))

            # Weird special case where the engine returns "play pass"
            # and no actual analysis
            if analysis == "play pass":
                victim_move = "pass"
            else:
                analyses.append(analysis)
                analysis_move_regex = re.compile(r"play ([A-Z][0-9]{1,2}|pass)")
                victim_move = get_msg(analysis_move_regex).group(1)
        else:
            send_msg(to_engine, f"genmove {victim_color}")
            move_regex = re.compile(r"= ([A-Z][0-9]{1,2}|pass)")
            victim_move = get_msg(move_regex).group(1)

        game.play_move(Move.from_str(victim_move))
        maybe_print(f"\nTurn {turn}")
        maybe_print(f"KataGo played: {victim_move}")

        take_turn()

        turn += 1

    if verbose:
        print_kata_board()

    # What is the final score?
    black_score, white_score = game.score()
    our_margin = white_score - black_score
    if our_margin > 0:
        maybe_print(f"White won, up {our_margin} points.")
    elif our_margin < 0:
        maybe_print(f"Black won, up {our_margin} points.")
    else:
        maybe_print("Tie")

    send_msg(to_engine, "clear_board")

    return game, analyses


def run_baseline_attack(
    model_path: Path,
    adversarial_policy: str,
    num_playouts: int,
    passing_behavior: str,
    gpu: Optional[int] = None,
    *,
    allow_suicide: bool = False,
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
) -> Sequence[Game]:
    """Run a baseline attack against KataGo."""
    if adversarial_policy not in POLICIES:
        raise ValueError(
            f"Invalid policy '{adversarial_policy}', must be one of {POLICIES}",
        )
    if passing_behavior not in PASSING_BEHAVIOR:
        raise ValueError(
            f"Invalid behavior '{passing_behavior}', must be one of {PASSING_BEHAVIOR}",
        )
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
        verbose,
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

    def make_policy() -> AdversarialPolicy:
        if policy_cls in (MyopicWhiteBoxPolicy, NonmyopicWhiteBoxPolicy):
            policy = policy_cls(
                game,
                victim_color.opponent(),
                allow_suicide,
                to_engine,
                from_engine,
            )  # pytype: disable=not-instantiable,wrong-arg-count
        else:
            policy = policy_cls(
                game,
                victim_color.opponent(),
                allow_suicide,
            )  # pytype: disable=not-instantiable
        return PassingWrapper(policy, moves_before_pass)

    send_msg(to_engine, f"boardsize {board_size}")

    random.seed(seed)
    policy_cls = POLICIES[adversarial_policy]
    victim_color = Color.from_str(victim)

    game_iter = range(num_games)
    if not verbose and progress_bar:
        game_iter = tqdm(game_iter, desc="Playing", unit="games")

    games = []
    for i in game_iter:
        if verbose:
            print(f"\n--- Game {i + 1} of {num_games} ---")

        game = Game(board_size=board_size)
        policy = make_policy()
        game, analyses = rollout_policy(
            game,
            policy,
            victim_color,
            from_engine,
            to_engine,
            log_analysis,
            verbose,
        )
        games.append(game)

        # Save the game to disk if necessary
        if log_dir:
            strat_title = adversarial_policy.capitalize()
            victim_name = "Black" if victim == "B" else "White"
            sgf = game.to_sgf(f"{strat_title} attack; {victim_name} victim")

            with open(log_dir / f"game_{i}.sgf", "w") as f:
                f.write(sgf)

        # Save the analysis file if needed
        if log_analysis:
            assert log_dir is not None
            analysis_log_dir = log_dir / "analyses"
            analysis_log_dir.mkdir(exist_ok=True, parents=True)
            with open(analysis_log_dir / f"game_{i}.txt", "w") as f:
                f.write("\n\n".join(analyses))

    scores = [game.score() for game in games]
    margins = [black - white for black, white in scores]
    print(f"\nAverage win margin: {sum(margins) / len(margins)}")

    return games
