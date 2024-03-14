"""Generates param YAMLs for h1--r9, then runs generate_paper_evaluations.yml on them."""

import subprocess
from pathlib import Path

# (name, path to h, final ckpt, adv)
RUNS = [
    (
        "h1",
        "ttseng-cp505-advtrain-spp082-lr01-20230728-170008",
        "t0-s61032960-d123492767",
        "cyclic-adv-s545065216.bin.gz",
    ),
    (
        "h2",
        "ttseng-cp505-h2-20230823-142646",
        "t0-s22387200-d128854386",
        "cyclic-r1-s149878784-d173957317.bin.gz",
    ),
    (
        "h3",
        "ttseng-cp505-h3-retry-20230921-202435",
        "t0-s15898624-d133021460",
        "cyclic-r2-s253266688-d237106366.bin.gz",
    ),
    (
        "h4",
        "ttseng-cp505-h4-20231009-143230",
        "t0-s10979072-d155357778",
        "cyclic-r3-s213334016-d294060288.bin.gz",
    ),
    (
        "h5",
        "ttseng-cp505-h5-20231121",
        "t0-s9905920-d75058636",
        "cyclic-r4-s982983936-d540500842.bin.gz",
    ),
    (
        "h6",
        "ttseng-cp505-h6-fix-20231212",
        "t0-s19897600-d86709525",
        "cyclic-r5-s534912256-d674880880.bin.gz",
    ),
    (
        "h7",
        "ttseng-cp505-h7-20231218",
        "t0-s13333248-d93202834",
        "cyclic-r6-s228355840-d732306376.bin.gz",
    ),
    (
        "h8",
        "ttseng-cp505-h8-20231229",
        "t0-s32231168-d102479664",
        "cyclic-r7-s372472576-d825643292.bin.gz",
    ),
    (
        "h9",
        "ttseng-cp505-h9-240113",
        "t0-s71170048-d121232876",
        "cyclic-r8-s230162176-d883662666.bin.gz",
    ),
]

for name, path, final_checkpoint, adv_path in RUNS:
    adv_name = "r" + str(int(name[1:]) - 1)
    output_dir = Path(name)
    output_dir.mkdir(exist_ok=True)
    params_file = output_dir / "params.yml"
    with open(params_file, "w") as f:
        f.write(
            f"""# Experiment: evaluate several adversary checkpoints throughout training.
training_checkpoint_sweep:
  # Path to all models from the training run.
  checkpoints_paths:
    - path: /shared/victimplay/{path}/iteration-0
      last_checkpoint: {final_checkpoint}
  results_dir: "/shared/match/ttseng-iterated-adv-train-sweeps-240312/h/{name}"
  job_prefix: {name}
  adversary_algorithm: MCTS
  adversary_visits:
    - 16
    - 256
  # How many games to run between a adversary checkpoint and a victim.
  num_games_per_matchup: 50
  checkpoints_per_job: 12
  commit: 1553c05
  victims:
    - name: {adv_name}-v600
      filename: {adv_path}
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
