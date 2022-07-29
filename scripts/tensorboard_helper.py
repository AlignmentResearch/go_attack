"""Creates dummy folder symlinking to multiple training runs to appease TensorBoard.

By default, when we stop and resume katago training, it will create multiple
tfevents files in a single folder. TensorBoard doesn't like this.

This script creates a dummy folder that contains subdirectories, each of which
is symlinked to the actual tfevents. This let's us run Tensorboard more nicely.

Example of running this script:
    python scripts/tensorboard_helper.py --base_dir selfplay-training/test0/

After running, you can launch tensorboard like this:
    tensorboard --logdir=selfplay-training/test0/tensorboard_logdir
"""

import dataclasses
import os
import pathlib

from simple_parsing import ArgumentParser


@dataclasses.dataclass
class Config:
    """Configs for argument parsing."""

    base_dir: str  # The directory where selfplay / victimplay training occurs.


def main(cfg: Config):
    """Main entrypoint: creates dummy folder with symlinks to tfevents files."""
    tensorboard_logdir = os.path.join(cfg.base_dir, "tensorboard_logdir")
    pathlib.Path(tensorboard_logdir).mkdir(exist_ok=True)

    src_train_dir = os.path.join(cfg.base_dir, "train")
    run_names = [
        x
        for x in os.listdir(src_train_dir)
        if os.path.isdir(os.path.join(src_train_dir, x))
    ]

    for run_name in run_names:
        src_run_dir = os.path.join(src_train_dir, run_name)
        tfevent_names = [
            x for x in os.listdir(src_run_dir) if x.startswith("events.out.tfevents.")
        ]

        for tfevent_name in tfevent_names:
            dst_run_dir = os.path.join(
                tensorboard_logdir,
                "-".join([run_name] + tfevent_name.split(".")[-2:]),
            )
            pathlib.Path(dst_run_dir).mkdir(exist_ok=True)

            # For some reason symlinks don't work with tensorboard,
            # only hardlinks do...
            try:
                os.link(
                    src=os.path.join(src_run_dir, tfevent_name),
                    dst=os.path.join(dst_run_dir, tfevent_name),
                )
            except FileExistsError:
                print(f"train/{run_name}/{tfevent_name} already linked.")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_arguments(Config, dest="cfg")
    main(parser.parse_args().cfg)
