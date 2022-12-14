"""Functions for running baseline attacks against KataGo."""
import itertools
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

ENGINE_TYPES = (
    "elf",
    "leela",
    "katago",
)

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
    engine_type: str,
    config_path: Optional[Path] = None,
    model_path: Optional[Path] = None,
    num_visits: Optional[int] = None,
    passing_behavior: Optional[str] = None,
    gpu: Optional[int] = None,
    verbose: bool = False,
) -> Tuple[IO[bytes], IO[bytes]]:
    """Starts the engine, returning a tuple with the engines stdin and stdout."""
    katago_required_args = {
        "config_path": config_path,
        "model_path": model_path,
        "num_visits": num_visits,
        "passing_behavior": passing_behavior,
    }
    if engine_type == "katago":
        for arg_name, arg_value in katago_required_args.items():
            if arg_value is None:
                raise ValueError(f"{arg_name} must not be None")
        if passing_behavior not in PASSING_BEHAVIOR:
            raise ValueError(
                f"Invalid behavior '{passing_behavior}', must be one of "
                f"{PASSING_BEHAVIOR}",
            )
        if config_path and not config_path.exists():
            raise ValueError(f"config_path must exist: {config_path}")
        if model_path and not model_path.exists():
            raise ValueError(f"model_path must exist: {model_path}")
        if gpu is None:
            gpu = select_best_gpu(10)

        args = [
            str(executable_path),
            "gtp",
            "-model",
            str(model_path),
            "-override-config",
            f"passingBehavior={passing_behavior},maxVisits={num_visits}",
            "-config",
            str(config_path),
        ]
        env = {"CUDA_VISIBLE_DEVICES": str(gpu)}
    else:
        for arg_name, arg_value in katago_required_args.items():
            if arg_value is not None:
                print(f"Warning: Ignoring argument {arg_name}={arg_value}")
        if gpu is not None:
            print(f"Warning: Ignoring argument gpu=f{gpu}")

        args = [str(executable_path)]
        env = {}

    if verbose:
        print(f"Starting engine with args: {args}")
    proc = Popen(
        args,
        bufsize=0,  # We need to disable buffering to get stdout line-by-line
        env=env,
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
    adversarial_policy: str,
    model_path: Optional[Path],
    num_visits: Optional[int],
    passing_behavior: Optional[str],
) -> Path:
    """Make a log directory and return the Path to it."""
    desc_list = []
    if model_path is not None:
        desc_list.append(f"model={model_path.stem}")
    desc_list.append(f"policy={adversarial_policy}")
    if num_visits is not None:
        desc_list.append(f"visits={num_visits}")
    if passing_behavior is not None:
        desc_list.append(f"pass={passing_behavior}")
    desc = "_".join(desc_list)

    log_dir = log_root / desc
    log_dir.mkdir(exist_ok=True, parents=True)
    print(f"Logging SGF game files to '{str(log_dir)}'")
    return log_dir


def rollout_policy(
    game: Game,
    policy: AdversarialPolicy,
    victim_color: Color,
    engine_type: str,
    from_engine: IO[AnyStr],
    to_engine: IO[AnyStr],
    log_analysis: bool,
    verbose: bool,
) -> Tuple[Game, Sequence[str]]:
    """Rollouts `policy` against engine with pipe `from_engine`."""
    # Regex that matches the "=" printed after a successful command that has no
    # output.
    SUCCESS_REGEX = re.compile(r"^=")
    LEELA_SHOWBOARD_END_REGEX = re.compile(r"^Black time:")
    from_engine_lines = map(lambda line: line.decode("ascii").strip(), from_engine)

    def maybe_print(msg):
        if verbose:
            print(msg)

    def print_engine_board():
        send_msg(to_engine, "showboard")
        # The different engines have different showboard formats.
        predicates = {
            "elf": lambda _, msg: not SUCCESS_REGEX.fullmatch(msg),
            "leela": lambda _, msg: not LEELA_SHOWBOARD_END_REGEX.match(msg),
            "katago": lambda index, _: index < game.board_size + 3,
        }
        for _, msg in itertools.takewhile(
            lambda tup: predicates[engine_type](*tup),
            enumerate(from_engine_lines),
        ):
            print(msg)

    def get_msg(pattern: re.Pattern) -> re.Match:
        while True:
            msg = next(from_engine_lines)
            if hit := pattern.fullmatch(msg):
                return hit

    def take_turn():
        move = policy.next_move()
        game.play_move(move)

        vertex = str(move) if move else "pass"
        send_msg(to_engine, f"play {victim_color.opponent()} {vertex}")
        maybe_print("Passing" if move is None else f"Playing {vertex}")

        get_msg(SUCCESS_REGEX)

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
            move_regex = re.compile(r"= ([A-Z][0-9]{1,2}|pass)", re.IGNORECASE)
            victim_move = get_msg(move_regex).group(1)

        maybe_print(f"\nTurn {turn}")
        maybe_print(f"{engine_type} played: {victim_move}")
        game.play_move(Move.from_str(victim_move))

        if game.is_over():
            break

        take_turn()

        turn += 1

    # ELF automatically resets the game when the game is over, so printing the
    # board for ELF would just give a blank new board.
    if verbose and engine_type != "elf":
        print_engine_board()

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
    adversarial_policy: str,
    model_path: Optional[Path] = None,
    num_visits: Optional[int] = None,
    passing_behavior: Optional[str] = None,
    gpu: Optional[int] = None,
    *,
    allow_suicide: bool = False,
    board_size: int = 19,
    config_path: Path,
    engine_type: str,
    executable_path: Path,
    komi: float = 6.5,
    log_analysis: bool = False,
    log_root: Optional[Path] = None,
    moves_before_pass: int = 211,
    num_games: int = 1,
    progress_bar: bool = True,
    seed: int = 42,
    verbose: bool = False,
    victim: Literal["B", "W"] = "B",
) -> Sequence[Game]:
    """Run a baseline attack."""
    if adversarial_policy not in POLICIES:
        raise ValueError(
            f"Invalid policy '{adversarial_policy}', must be one of {POLICIES}",
        )

    # Start up the executable.
    to_engine, from_engine = start_engine(
        executable_path,
        engine_type,
        config_path,
        model_path,
        num_visits,
        passing_behavior,
        gpu,
        verbose,
    )

    log_dir = None
    if log_root is not None:
        log_dir = make_log_dir(
            log_root,
            adversarial_policy,
            model_path,
            num_visits,
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
    send_msg(to_engine, f"komi {komi}")

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

        game = Game(board_size=board_size, komi=komi)
        policy = make_policy()
        game, analyses = rollout_policy(
            game,
            policy,
            victim_color,
            engine_type,
            from_engine,
            to_engine,
            log_analysis,
            verbose,
        )
        games.append(game)

        # Save the game to disk if necessary
        if log_dir:
            adv_name = f"adv-baseline-{adversarial_policy}"
            victim_name = "victim"
            sgf = game.to_sgf(
                comment=(
                    f"{adversarial_policy.capitalize()} attack; "
                    f"{'Black' if victim == 'B' else 'White'} victim"
                ),
                black_name=(victim_name if victim == "B" else adv_name),
                white_name=(adv_name if victim == "B" else victim_name),
            )

            with open(log_dir / f"game_{i}.sgf", "w") as f:
                f.write(sgf)

        # Save the analysis file if needed
        if log_analysis:
            assert log_dir is not None
            analysis_log_dir = log_dir / "analyses"
            analysis_log_dir.mkdir(exist_ok=True, parents=True)
            with open(analysis_log_dir / f"game_{i}.txt", "w") as f:
                f.write("\n\n".join(analyses))
    send_msg(to_engine, "quit")

    scores = [game.score() for game in games]
    margins = [black - white for black, white in scores]
    print(f"\nAverage win margin: {sum(margins) / len(margins)}")

    return games
