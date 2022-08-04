"""Run a hardcoded adversarial attack against KataGo."""

from argparse import ArgumentParser
from pathlib import Path

from go_attack.adversarial_policy import POLICIES
from go_attack.baseline_attack import run_baseline_attack


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
        default="edge",
        help="Adversarial policy to use",
        # nargs="+",
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

    # The mirror policy only makes sense when we're attacking black because we need
    # the victim to play first in order to know where to play next
    if args.policy == "mirror" and args.victim != "B":
        raise ValueError("Mirror policy only works when victim == black")

    # Try to find the config file automatically
    config_path = args.config
    if config_path is None:
        config_path = Path("go_attack") / "configs" / "katago" / "baseline_attack.cfg"

    # Try to find the executable automatically
    katago_exe = args.executable
    if katago_exe is None:
        katago_exe = Path("/engines") / "KataGo-custom" / "cpp" / "katago"
        assert katago_exe.exists(), "Could not find KataGo executable"

    # Try to find the model automatically
    if args.model is None:
        root = Path("/go_attack") / "models"
        model_path = min(
            root.glob("*.bin.gz"),
            key=lambda x: x.stat().st_size,
            default=None,
        )
        if model_path is None:
            raise FileNotFoundError("Could not find model; please set the --model flag")
    else:
        model_path = args.model
        assert model_path.exists(), "Could not find model"

    print(f"Running {args.policy} attack baseline\n")
    print(f"Using KataGo executable at '{str(katago_exe)}'")
    print(f"Using model at '{str(model_path)}'")
    print(f"Using config file at '{str(config_path)}'")

    games = run_baseline_attack(
        args.policy,
        args.passing_behavior,
        config_path,
        katago_exe,
        model_path,
        board_size=args.size,
        log_dir=args.log_dir,
        num_games=args.num_games,
        num_playouts=args.num_playouts,
        seed=args.seed,
        victim=args.victim,
        verbose=args.verbose,
    )

    scores = [game.score() for game in games]
    margins = [black - white for black, white in scores]
    print(f"\nAverage win margin: {sum(margins) / len(margins)}")


if __name__ == "__main__":
    main()
