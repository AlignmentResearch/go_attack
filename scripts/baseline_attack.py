"""Run a hardcoded adversarial attack against KataGo."""

from argparse import ArgumentParser
from functools import partial
from itertools import product
from multiprocessing import Pool
from pathlib import Path

from pynvml import nvmlDeviceGetCount, nvmlInit, nvmlShutdown

from go_attack.adversarial_policy import POLICIES
from go_attack.baseline_attack import (
    ENGINE_TYPES,
    PASSING_BEHAVIOR,
    run_baseline_attack,
)


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
        "--engine",
        choices=ENGINE_TYPES,
        default="katago",
        help="The type of engine that the victim is running on",
    )
    # Because ELF OpenGo disallows suicide moves and we want to launch
    # consistent attacks across all engines, we default to disallowing suicide
    # moves.
    parser.add_argument(
        "--allow-suicide",
        action="store_true",
        help="Allow the adversary to make suicide moves",
    )
    parser.add_argument(
        "--passing-behavior",
        choices=PASSING_BEHAVIOR,
        help="Behavior that KataGo uses when passing",
        nargs="+",
        type=str,
    )
    parser.add_argument(
        "--models", type=Path, default=None, help="KataGo model weights", nargs="+"
    )
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
        help="Number of moves before accepting a pass from the victim and ending the game",
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
    if args.engine == "katago":
        if args.num_playouts is None:
            args.num_playouts = [512]
        if args.passing_behavior is None:
            args.passing_behavior = ["standard"]

    # The mirror policy only makes sense when we're attacking black because we need
    # the victim to play first in order to know where to play next
    if args.policy == "mirror" and args.victim != "B":
        raise ValueError("Mirror policy only works when victim == black")

    config_path = args.config
    if args.engine == "katago":
        # Try to find the config file automatically
        if config_path is None:
            config_path = (
                Path("/go_attack") / "configs" / "katago" / "baseline_attack.cfg"
            )
        if not config_path.exists():
            raise FileNotFoundError("Could not find config file")
        print(f"Using config file at '{str(config_path)}'")

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
        print(f"Using models at '{list(map(str, model_paths))}'")  # type: ignore

    # Try to find the executable automatically
    executable_path = args.executable
    if executable_path is None and args.engine == "katago":
        executable_path = Path("/engines") / "KataGo-custom" / "cpp" / "katago"
    if not executable_path.exists():
        raise FileNotFoundError("Could not find executable")
    print(f"Using executable at '{str(executable_path)}'")

    print(f"Running {args.policy} attack baseline\n")
    baseline_fn = partial(
        run_baseline_attack,
        allow_suicide=args.allow_suicide,
        board_size=args.size,
        config_path=config_path,
        engine_type=args.engine,
        executable_path=executable_path,
        log_analysis=args.log_analysis,
        log_root=args.log_dir,
        moves_before_pass=args.moves_before_pass,
        num_games=args.num_games,
        seed=args.seed,
        verbose=args.verbose,
        victim=args.victim,
    )

    configs = (
        list(
            product(args.policy, model_paths, args.num_playouts, args.passing_behavior)
        )
        if args.engine == "katago"
        else list(product(args.policy))
    )

    if len(configs) > 1:
        print(f"Running {len(configs)} configurations in parallel")
        if args.engine != "katago":
            print(
                f"WARNING: {args.engine} is not set up for parallel runs, as the "
                f"`socat` setup for {args.engine} does not support scheduling runs "
                "on different GPUs. Parallelize runs by launching a separate "
                "instance of baseline_attack vs. a separate instance of "
                f"{args.engine}."
            )
            raise ValueError(f"Parallel runs not supported for engine: {args.engine}")

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
