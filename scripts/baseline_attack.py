"""Run a hardcoded adversarial attack against KataGo."""

from argparse import ArgumentParser
from functools import partial
from itertools import product
from multiprocessing import Pool
from pathlib import Path

from pynvml import nvmlDeviceGetCount, nvmlInit, nvmlShutdown

from go_attack.adversarial_policy import POLICIES
from go_attack.baseline_attack import PASSING_BEHAVIOR, run_baseline_attack


def main():  # noqa: D103
    parser = ArgumentParser(
        description="Run a hardcoded adversarial attack against KataGo",
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
        choices=PASSING_BEHAVIOR,
        default=["standard"],
        help="Behavior that KataGo uses when passing",
        nargs="+",
        type=str,
    )
    parser.add_argument("--models", type=Path, default=None, help="model", nargs="+")
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
        default=[512],
        help="Maximum number of MCTS playouts KataGo is allowed to use",
        nargs="+",
    )
    parser.add_argument("--log-analysis", action="store_true", help="Log analysis")
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Where to save logged games",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--size", type=int, default=19, help="Board size")
    parser.add_argument(
        "--policy",
        type=str,
        choices=tuple(POLICIES),
        default=["edge"],
        help="Adversarial policies to use",
        nargs="+",
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
        help="The color the victim plays as (black or white)",
    )
    args = parser.parse_args()

    # The mirror policy only makes sense when we're attacking black because we need
    # the victim to play first in order to know where to play next
    if args.policy == "mirror" and args.victim != "B":
        raise ValueError("Mirror policy only works when victim == black")

    # Try to find the config file automatically
    config_path = args.config
    if config_path is None:
        config_path = Path("/go_attack") / "configs" / "katago" / "baseline_attack.cfg"
    if not config_path.exists():
        raise FileNotFoundError("Could not find config file")

    # Try to find the executable automatically
    katago_exe = args.executable
    if katago_exe is None:
        katago_exe = Path("/engines") / "KataGo-custom" / "cpp" / "katago"
    if not katago_exe.exists():
        raise FileNotFoundError("Could not find KataGo executable")

    # Try to find the model automatically
    if args.models is None:
        root = Path("/go_attack") / "models"
        model_paths = [
            min(
                root.glob("*.gz"),
                key=lambda x: x.stat().st_size,
                default=None,
            ),
        ]
        if model_paths[0] is None:
            raise FileNotFoundError(
                "Could not find model; please set the --models flag",
            )
    else:
        model_paths = args.models
        if not all(p.exists() for p in model_paths):
            raise FileNotFoundError("Could not find model")

    print(f"Running {args.policy} attack baseline\n")
    print(f"Using KataGo executable at '{str(katago_exe)}'")
    print(f"Using models at '{list(map(str, model_paths))}'")  # type: ignore
    print(f"Using config file at '{str(config_path)}'")

    baseline_fn = partial(
        run_baseline_attack,
        board_size=args.size,
        config_path=config_path,
        executable_path=katago_exe,
        log_analysis=args.log_analysis,
        log_root=args.log_dir,
        moves_before_pass=args.moves_before_pass,
        num_games=args.num_games,
        seed=args.seed,
        verbose=args.verbose,
        victim=args.victim,
    )
    configs = list(
        product(model_paths, args.policy, args.num_playouts, args.passing_behavior),
    )

    if len(configs) > 1:
        print(f"Running {len(configs)} configurations in parallel")

        nvmlInit()
        num_devices = min(len(configs), nvmlDeviceGetCount())
        print(f"Using {num_devices} GPU devices")

        with Pool(2 * num_devices) as p:
            baseline_fn = partial(baseline_fn, progress_bar=False)
            configs = [(*config, i % num_devices) for i, config in enumerate(configs)]
            p.starmap(baseline_fn, configs)

        nvmlShutdown()
    else:
        baseline_fn(*configs[0])


if __name__ == "__main__":
    main()
