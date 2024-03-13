"""Generates param YAMLs for r1--r9, then runs generate_paper_evaluations.yml on them."""

import subprocess
from pathlib import Path

# (name, adv paths + final ckpt, path to victim, number of checkpoints to test)
RUNS = [
    (
        "r1",
        [("ttseng-cyclic-reattack-20230803", "t0-s149878784-d173957317")],
        "ttseng-cp505-advtrain-spp082-20230728-s61032960.bin.gz",
        30,
    ),
    (
        "r2",
        [("tony-cyclic-reattack2-20230901", "t0-s253266688-d237106366")],
        "cp505-h2-s22387200-d128854386.bin.gz",
        30,
    ),
    (
        "r3",
        [
            ("ttseng-cyclic-r3-20231002", "t0-s81496832-d260697484"),
            ("ttseng-cyclic-r3-20231005", "t0-s11976704-d263936137"),
            ("ttseng-cyclic-r3-20231006-0035", "t0-s119860480-d294060288"),
        ],
        "cp505-h3-s15898624-d133021460.bin.gz",
        30,
    ),
    (
        "r4",
        [("ttseng-cyclic-r4-20231010", "t0-s982983936-d540500842")],
        "cp505-h4-s10979072-d155357778.bin.gz",
        60,
    ),
    (
        "r5",
        [("ttseng-cyclic-r5-20231123", "t0-s534912256-d674880880")],
        "cp505-h5-s9905920-d75058636.bin.gz",
        45,
    ),
    (
        "r6",
        [("ttseng-cyclic-r6-20231213", "t0-s228355840-d732306376")],
        "cp505-h6-s19897600-d86709525.bin.gz",
        30,
    ),
    (
        "r7",
        [("ttseng-cyclic-r7-20231219", "t0-s372472576-d825643292")],
        "cp505-h7-s13333248-d93202834.bin.gz",
        30,
    ),
    (
        "r8",
        [("ttseng-cyclic-r8-20231231", "t0-s230162176-d883662666")],
        "cp505-h8-s32231168-d102479664.bin.gz",
        30,
    ),
    (
        "r9",
        [("ttseng-cyclic-r9-20240119", "t0-s275431168-d952530928")],
        "cp505-h9-s71170048-d121232876.bin.gz",
        30,
    ),
]

for name, paths, victim_path, num_checkpoints in RUNS:
    victim_name = name.replace("r", "h")
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
            f"""# Experiment: evaluate several adversary checkpoints throughout training.
training_checkpoint_sweep:
  # Path to all models from the training run.
  {checkpoints_paths}
  results_dir: "/shared/match/ttseng-iterated-adv-train-sweeps-240312/{name}"
  job_prefix: {name}
  adversary_algorithm: AMCTS
  adversary_visits:
    - 600
  # Maximum number of checkpoints to evaluate
  num_checkpoints_to_evaluate: {num_checkpoints}
  # How many games to run between a adversary checkpoint and a victim.
  num_games_per_matchup: 50
  checkpoints_per_job: 15
  commit: 1553c05
  victims:
    - name: {victim_name}-v16
      filename: {victim_path}
      visits: 16
    - name: {victim_name}-v256
      filename: {victim_path}
      visits: 256"""
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
