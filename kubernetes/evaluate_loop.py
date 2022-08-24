from argparse import ArgumentParser
from pathlib import Path
import os
import time


def main(args):
    run_dir = args.root_dir / args.run_name
    models_dir = run_dir / "models"
    output_dir = run_dir / "eval"
    log_dir = output_dir / "logs"
    sgf_dir = output_dir / "sgfs"
    log_dir.mkdir(exist_ok=True, parents=True)
    sgf_dir.mkdir(exist_ok=True, parents=True)
    prev_models = set()

    while True:
        # Are there any new models?
        models = set(models_dir.rglob("*.bin.gz"))
        models -= prev_models

        for model in models:
            model_id = model.parent.stem
            print(f"Evaluating model '{model_id}'")

            os.system(
                " ".join([
                    args.executable,
                    "-config",
                    args.config,
                    f"-log-file {log_dir / model_id}.log",
                    f"-override-config nnModelFile0={args.victim}",
                    f"-override-config nnModelFile1={model}",
                    f"-override-config numGamesTotal={args.games_per_ckpt}",
                    f"-sgf-output-dir {sgf_dir}",
                ])
            )
            prev_models.add(model)

        time.sleep(args.poll_interval)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("run_name", type=str)
    parser.add_argument("victim", type=Path, help="Path to victim model")
    parser.add_argument(
        "--config", type=str, default="/go_attack/configs/match.cfg",
        help="Path to config file"
    )
    parser.add_argument(
        "--executable", type=str, default="/engines/KataGo-custom/cpp/katago",
        help="Path to the KataGo executable inside the Docker container"
    )
    parser.add_argument(
        "--games-per-ckpt", type=int, default=100,
        help="Number of eval games to play for each checkpoint"
    )
    parser.add_argument(
        "--model-dir", type=Path, default="models",
        help="Directory to look for checkpoints in."
    )
    parser.add_argument(
        "--poll-interval", type=int, default=30,
        help="How often to check for new models, in seconds."
    )
    parser.add_argument(
        "--root-dir", type=Path, default="/shared/victimplay",
        help="Parent directory for the run folder."
    )
    main(parser.parse_args())
