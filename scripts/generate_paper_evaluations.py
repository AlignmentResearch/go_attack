"""Generates config files for the main experiments in paper.

Experiments:
* Evaluate adversary against several victims with a large number of games.
* Evaluate various adversary checkpoints throughout training.
* Evaluate adversary vs. victim with varying victim visits.
* Evaluate adversary vs. victim with varying adversary visits.
"""
import argparse
import getpass
import itertools
import math
import os
import re
import subprocess
from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, TextIO

import numpy as np
import yaml

UsageString = namedtuple("UsageString", ["usage_string", "command"])


class Devbox:
    def __init__(
        self,
        to_devbox: subprocess.PIPE,
        from_devbox: subprocess.PIPE,
    ):
        self.to_devbox = to_devbox
        self.from_devbox = from_devbox

    def run(self, command: str) -> str:
        self.__write(command)
        return self.__read_output()

    def clear_output(self):
        self.__read_output()

    def __write(self, command: str):
        self.to_devbox.write(f"{command}\n".encode("ascii"))

    def __read_output(self):
        # Output a token to know when to stop reading.
        end_token = "__done"
        self.__write(f"echo '{end_token}'")
        output_lines = itertools.takewhile(
            lambda line: line != end_token,
            map(lambda line: line.decode("ascii").rstrip(), self.from_devbox),
        )
        return "\n".join(output_lines)


@contextmanager
def create_devbox():
    devbox_name = f"{get_user()}-devbox-gen-evals"
    subprocess.run(
        [
            "ctl",
            "devbox",
            "run",
            "--gpu",
            "0",
            "--cpu",
            "1",
            "--name",
            devbox_name,
            "--shared-host-dir",
            "/nas/ucb/k8/go-attack",
            "--shared-host-dir-mount",
            "/shared",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    try:
        print("Waiting for devbox to start...")
        while True:
            output = subprocess.run(
                ["ctl", "job", "list"], capture_output=True, check=True
            ).stdout.decode("ascii")
            if any(
                devbox_name in line and "Running" in line for line in output.split("\n")
            ):
                break

        proc = subprocess.Popen(
            ["ctl", "devbox", "ssh", "--name", devbox_name],
            bufsize=0,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        devbox = Devbox(to_devbox=proc.stdin, from_devbox=proc.stdout)
        # Clear any initialization output.
        devbox.clear_output()
        yield Devbox(to_devbox=proc.stdin, from_devbox=proc.stdout)
        proc.terminate()
    finally:
        print("Deleting devbox...")
        subprocess.run(
            ["ctl", "devbox", "del", "--name", devbox_name],
            check=True,
            stdout=subprocess.DEVNULL,
        )


def get_user() -> str:
    return getpass.getuser()


def str_to_comment(s: str) -> str:
    """Prepends '# ' to every line in a string."""
    return "".join(f"# {line}\n" for line in s.splitlines())


def get_usage_string(
    repo_root: Path,
    description: str,
    job_name: str,
    default_num_gpus: int,
    num_games: int,
    configs: Iterable[Path],
) -> UsageString:
    configs = [
        re.sub(r".*go_attack/configs", r"/go_attack/configs", str(config))
        for config in configs
    ]
    config_flags = " ".join(f"-config {config}" for config in configs)
    command = f"""\
    {repo_root}/kubernetes/launch-match.sh --gpus {default_num_gpus} \\
    --games {num_games} {get_user()}-{job_name} -- {config_flags}"""
    usage_string = f"""\
Experiment: {description}
Command:
{command}"""
    return UsageString(usage_string=usage_string, command=command)


def get_adversary_steps(adversary_path: Path) -> str:
    match = re.search("t0-s([0-9]+)-", adversary_path)
    if match:
        return match.group(1)
    else:
        return "UNKNOWN"


def write_bot(
    f: TextIO,
    bot_index: int,
    bot_path: str,
    bot_name: str,
    num_visits: int,
    bot_algorithm: str,
    extra_parameters: Iterable[Dict[str, str]] = {},
):
    f.write(
        f"""\
nnModelFile{bot_index} = {bot_path}
botName{bot_index} = {bot_name}
maxVisits{bot_index} = {num_visits}
searchAlgorithm{bot_index} = {bot_algorithm}
"""
    )
    for param in extra_parameters:
        f.write(f"{param['key']}{bot_index} = {param['value']}\n")


def write_victims(
    f: TextIO, victims: Iterable[Dict[str, Any]], bot_index_offset: int = 0
):
    for i, victim in enumerate(victims):
        if i > 0:
            f.write('\n')
        write_bot(
            f=f,
            bot_index=bot_index_offset + i,
            bot_path=f"/shared/victims/{victim['filename']}",
            bot_name=victim["name"],
            num_visits=victim["visits"],
            bot_algorithm="MCTS",
            extra_parameters=victim.get("extra_parameters", []),
        )


def generate_main_adversary_evaluation(
    parameters: Dict[str, Any],
    config_dir: Path,
    repo_root: Path,
):
    common_parameters = parameters
    parameters = parameters["main_adversary_evaluation"]
    output_config = config_dir / "main_adversary_evaluation.cfg"

    victims = parameters["victims"]
    num_games_total = len(victims) * parameters["num_games_per_matchup"]
    usage_string = get_usage_string(
        repo_root=repo_root,
        description="evaluate the main adversary against several victims",
        job_name="eval",
        default_num_gpus=2,
        num_games=num_games_total,
        configs=[output_config],
    ).usage_string

    with open(output_config, "w") as f:
        f.write(str_to_comment(usage_string))

        f.write("logSearchInfo = false\n")
        f.write(f"numGamesTotal = {num_games_total}\n\n")
        f.write(f"numBots = {len(victims) + 1}\n")
        secondary_bots = ",".join(map(str, range(1, len(victims) + 1)))
        f.write(f"secondaryBots = {secondary_bots}\n\n")

        adversary_path = common_parameters["main_adversary"]["path"]
        num_adversary_visits = parameters["num_adversary_visits"]
        write_bot(
            f=f,
            bot_index=0,
            bot_path=adversary_path,
            bot_name=f"adv-s{get_adversary_steps(adversary_path)}-v{num_adversary_visits}",
            num_visits=num_adversary_visits,
            bot_algorithm="AMCTS-S",
        )
        write_victims(f=f, victims=parameters["victims"], bot_index_offset=1)

    print(f"\n{usage_string}\n")


def generate_training_checkpoint_sweep_evaluation(
    parameters: Dict[str, Any],
    config_dir: Path,
    repo_root: Path,
):
    common_parameters = parameters
    parameters = parameters["training_checkpoint_sweep"]

    evaluation_config_dir = config_dir / "training_checkpoint_sweep_evaluation"
    evaluation_config_dir.mkdir(parents=True, exist_ok=True)
    victim_config = evaluation_config_dir / "victims.cfg"
    victims = parameters["victims"]
    with open(victim_config, "w") as f:
        f.write("logSearchInfo = false\n")
        secondary_bots = ",".join(map(str, range(len(victims))))
        f.write(f"secondaryBots = {secondary_bots}\n\n")
        write_victims(f, victims)

    main_checkpoint_path = Path(common_parameters["main_adversary"]["path"])
    checkpoints_path = Path(parameters["checkpoints_path"])
    assert checkpoints_path in main_checkpoint_path.parents
    with create_devbox() as devbox:
        num_checkpoints = int(devbox.run(f"ls {checkpoints_path} | wc -l"))
        indices_to_evaluate = np.unique(
            np.linspace(
                0, num_checkpoints - 1, parameters["num_checkpoints_to_evaluate"]
            )
            .round()
            .astype(int)
        )
        checkpoints = devbox.run(f"ls -v {checkpoints_path}").split("\n")
        checkpoints_to_evaluate = [checkpoints[i] for i in indices_to_evaluate]
        main_checkpoint = main_checkpoint_path.parent.name
        if main_checkpoint not in checkpoints_to_evaluate:
            checkpoints_to_evaluate.append(main_checkpoint)

    # Each checkpoint costs GPU memory, so we cannot give every checkpoint to a
    # job if the number of checkpoints is high. Instead, we split the
    # checkpoints up among several jobs.
    # A more robust script would estimate this value dynamically based on victim
    # and checkpoint sizes, but for now we're hardcoding this based on the
    # following values:
    # * A b40c256 victim + a b20c256x2 victim + a b6c96 victim costs 5942MB.
    # * Each additional b6c96 checkpoint costs 815MB.
    # * We put enough checkpoints to hit 80% of the memory of a 16GB GPU,
    #   leaving the 20% remaining memory as buffer to account for error in this
    #   estimate.
    checkpoints_per_job = math.floor((16384 * 0.8 - 5942) / 815)
    num_jobs = math.ceil(len(checkpoints_to_evaluate) / checkpoints_per_job)
    num_adversary_visits = parameters["num_adversary_visits"]
    job_commands = []
    job_description = "evaluate several adversary checkpoints throughout training"
    for i in range(num_jobs):
        checkpoints_start = i * checkpoints_per_job
        checkpoints_end = min(
            (i + 1) * checkpoints_per_job, len(checkpoints_to_evaluate)
        )
        job_name = f"checkpoints-{checkpoints_start}-to-{checkpoints_end}"
        job_config = evaluation_config_dir / f"{job_name}.cfg"

        with open(job_config, "w") as f:
            job_checkpoints = checkpoints_to_evaluate[checkpoints_start:checkpoints_end]
            num_games = (
                len(victims)
                * len(job_checkpoints)
                * parameters["num_games_per_matchup"]
            )
            usage_string = get_usage_string(
                repo_root=repo_root,
                description=job_description,
                job_name=job_name,
                default_num_gpus=2,
                num_games=num_games,
                configs=[victim_config, job_config],
            )
            f.write(str_to_comment(usage_string.usage_string))
            job_commands.append(usage_string.command)

            f.write(f"numGamesTotal = {num_games}")
            f.write(f"numBots = {len(victims) + len(job_checkpoints)}")
            secondary_bots_2 = ",".join(
                map(lambda x: str(x + len(victims)), range(len(job_checkpoints)))
            )
            f.write(f"secondaryBots2 = {secondary_bots_2}\n")

            for j, checkpoint in enumerate(job_checkpoints):
                f.write("\n")
                write_bot(
                    f=f,
                    bot_index=len(victims) + j,
                    bot_path=Path(parameters["checkpoints_path"])
                    / checkpoint
                    / "model.bin.gz",
                    bot_name=f"adv-s{get_adversary_steps(checkpoint)}-v{num_adversary_visits}",
                    num_visits=num_adversary_visits,
                    bot_algorithm=parameters["adversary_algorithm"],
                )

    command = "\n".join(job_commands)
    print(f"\nExperiment: {job_description}\nCommand:\n{command}\n")


def main():
    """Entrypoint for the script."""
    parser = argparse.ArgumentParser(
        description="Generates config files for the main experiments in paper",
    )
    parser.add_argument(
        "parameter_file",
        type=Path,
        help="Path to YAML file providing parameters for the experiments.",
    )
    args = parser.parse_args()

    repo_root = Path(os.path.dirname(os.path.realpath(__file__))).parents[0]
    config_dir = repo_root / "configs"
    assert os.path.isdir(config_dir)

    with open(args.parameter_file) as f:
        evaluation_parameters = yaml.safe_load(f)

    generate_main_adversary_evaluation(
        evaluation_parameters,
        config_dir=config_dir,
        repo_root=repo_root,
    )
    generate_training_checkpoint_sweep_evaluation(
        evaluation_parameters,
        config_dir=config_dir,
        repo_root=repo_root,
    )

    # notes:
    #  - we'll need to replace /nas/ucb/k8 with /shared in the configs
    #  - print warning to user if path note found at either /nas/ucb/k8 nor
    #  /shared --- they need to run this inside a devbox or on a CHAI machine
    #  - at the top of the generating config files, should add a comment saying
    #  how to launch. also print the launch instructions once this script is
    #  done generating instructinos
    #
    # be helpful and print out the total num of games that each experiment will
    # take --- will help with determining GPU allocation?

    # minor todos:
    #  - find a YAML linter
    #  - add a crude integration test so that we can't completely break this
    #  script? actually idk if that's very feasible --- parsing the YAML isn't
    #  hard, it's checking to make sure that when u type ./launch-match or
    #  whatever that everything works


if __name__ == "__main__":
    main()
