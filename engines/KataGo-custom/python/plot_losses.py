import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main():
    DESCRIPTION = """Plots loss from PyTorch training."""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "dirs", help="Path to the training run directory", type=Path, nargs="+"
    )
    parser.add_argument(
        "-log-x", help="Plot the x-axis on a logarithmic scale", action="store_true"
    )
    parser.add_argument(
        "-log-y", help="Plot the y-axis on a logarithmic scale", action="store_true"
    )
    parser.add_argument(
        "-y-min",
        help="Minimum value on the y-axis",
        type=float,
    )
    parser.add_argument(
        "-y-max",
        help="Maximum value on the y-axis",
        type=float,
    )
    parser.add_argument(
        "-loss",
        help="Which loss to plot, e.g., p0loss for policy loss.  Defaults to total loss",
        default="loss",
    )
    parser.add_argument(
        "-output", help="Path to write the loss plot", type=Path, required=True
    )
    parser.add_argument(
        "-validation",
        help="Print validation loss instead of train loss",
        action="store_true",
    )
    args = parser.parse_args()

    for d in args.dirs:
        file_modifier = "val" if args.validation else "train"
        metrics_file = d / "train" / "t0" / f"metrics_{file_modifier}.json"
        nsamp_key = "nsamp_train" if args.validation else "nsamp"
        nsamps = []
        losses = []
        with open(metrics_file) as f:
            for line in f:
                metrics = json.loads(line)
                nsamps.append(metrics[nsamp_key])
                losses.append(metrics[args.loss])
        plt.plot(nsamps, losses, label=d.name)

    plt.xlabel("steps")
    plt.ylabel(args.loss)
    if args.y_min is not None:
        plt.ylim(args.y_min, None)
    if args.y_max is not None:
        plt.ylim(None, args.y_max)
    if args.log_x:
        plt.xscale("log")
    if args.log_y:
        plt.yscale("log")
    plt.legend()
    plt.savefig(args.output)


if __name__ == "__main__":
    main()
