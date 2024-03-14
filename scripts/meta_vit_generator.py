"""Generates param YAMLs for h1--r9, then runs generate_paper_evaluations.yml on them."""

import subprocess
from pathlib import Path

# (name, (path, last ckpt)[], num_checkpoints_to_evaluate, model suffix)
RUNS = [
    (
        "vit-b4",
        [("ttseng-vitp2b4c384-selfplay-231031", "t0-s253387264-d55238979")],
        30,
        ".pt",
    ),
    (
        "vit-b8",
        [("ttseng-vitp2b8c384-selfplay-231106", "t0-s553885440-d138132846")],
        60,
        ".pt",
    ),
    (
        "vit-b16",
        [
            ("ttseng-vitp2b16c384-selfplay-231124", "t0-s405153792-d108411059"),
            ("ttseng-vitp2b16c384-minrows10m-240103", "t0-s650025472-d167043571"),
        ],
        59,
        ".pt",
    ),
    (
        "b10",
        [("ttseng-b10-selfplay-231026", "t0-s419465984-d105544048")],
        45,
        "bin.gz",
    ),
]

for name, paths, num_checkpoints, model_suffix in RUNS:
    checkpoints_paths = []
    for path, last_checkpoint in paths:
        checkpoints_paths.append(
            f"    - path: /shared/victimplay/{path}\n      last_checkpoint: {last_checkpoint}"
        )
    checkpoints_paths = "checkpoints_paths:\n" + "\n".join(checkpoints_paths)

    output_dir = Path(name)
    output_dir.mkdir(exist_ok=True)
    params_file = output_dir / "params.yml"
    with open(params_file, "w") as f:
        f.write(
            f"""
# Experiment: evaluate several adversary checkpoints throughout training.
training_checkpoint_sweep:
  # Path to all models from the training run.
  {checkpoints_paths}
  results_dir: "/shared/match/ttseng-vit-selfplay-240314/{name}"
  job_prefix: {name}
  adversary_algorithm: MCTS
  adversary_visits:
    - 1
    - 256
  # How many games to run between a adversary checkpoint and a victim.
  num_games_per_matchup: 100
  num_checkpoints_to_evaluate: {num_checkpoints}
  model_suffix: {model_suffix}
  checkpoints_per_job: 15
  commit: 8a3bd77
  victims:
    - name: cyclic-s545m
      filename: cyclic-adv-s545065216.bin.gz
      algorithm: AMCTS
      visits: 600
    - name: attack-vit-s326m
      filename: attack-vit-s325780992-d218287399.bin.gz
      algorithm: AMCTS
      visits: 600"""
        )

    # It'd be cleaner to import generate_paper_evaluations as a library instead
    # of calling it via a subprocess but I'm too lazy to refactor.
    subprocess.run(
        ["python", "generate_paper_evaluations.py", "--output", name, str(params_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        text=True,
    )
