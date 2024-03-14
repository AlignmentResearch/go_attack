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
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any, Iterable, List, Mapping, Sequence, Union

import natsort
import numpy as np
import yaml


@dataclass
class UsageString:
    """A usage string.

    Attributes:
        usage_string: The full usage string.
        command: The command contained in the usage string.
    """

    usage_string: str
    command: str


def adjust_nas_path(p: str) -> str:
    """Adjusts a path for certain container jobs."""
    return p.replace("/nas/ucb/k8/go-attack/", "/shared/")


class Devbox:
    """Allows executing commands on a running devbox."""

    def __init__(
        self,
        to_devbox: IO[bytes],
        from_devbox: IO[bytes],
    ):
        """Initializes the class with the I/O pipes to the devbox."""
        self.to_devbox = to_devbox
        self.from_devbox = from_devbox
        # Clear any unread output from the devbox, (e.g., output from devbox
        # initialization).
        self.__read_output()

    def run(self, command: str) -> str:
        """Executes a command on the devbox and returns the output."""
        self.__write(command)
        return self.__read_output()

    def __write(self, command: str):
        """Writes a command to the devbox."""
        self.to_devbox.write(f"{command}\n".encode("ascii"))

    def __read_output(self):
        """Reads output from the devbox."""
        # Output a token to know when to stop reading.
        end_token = "__done"
        self.__write(f"echo '{end_token}'")
        output_lines = itertools.takewhile(
            lambda line: line != end_token,
            map(lambda line: line.decode("ascii").rstrip(), self.from_devbox),
        )
        return "\n".join(output_lines)


@contextmanager
def create_dummy_devbox():
    """Yields a dummy "Devbox" that just uses the local filesystem."""
    proc = subprocess.Popen(
        ["bash"],
        bufsize=0,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    yield Devbox(to_devbox=proc.stdin, from_devbox=proc.stdout)
    proc.terminate()


def get_user() -> str:
    """Gets the name of the user."""
    return getpass.getuser()


def str_to_comment(s: str) -> str:
    """Prepends '# ' to every line in a string."""
    return "".join(f"# {line}\n" for line in s.splitlines())


def get_usage_string(
    repo_root: Path,
    job_description: str,
    job_name: str,
    default_num_gpus: int,
    num_games: int,
    configs: Iterable[Path],
) -> UsageString:
    """Generates a usage string for a job."""
    configs = [
        re.sub(r".*go_attack/configs", r"/go_attack/configs", str(config))
        for config in configs
    ]
    config_flags = " ".join(f"-config {config}" for config in configs)
    command = f"""\
    {repo_root}/kubernetes/launch-match.sh --gpus {default_num_gpus} \\
    --games {num_games} {get_user()}-{job_name} -- {config_flags}"""
    usage_string = f"""\
Experiment: {job_description}
Command:
{command}"""
    return UsageString(usage_string=usage_string, command=command)


def get_adversary_steps(adversary_path: str) -> str:
    """Fetches the adversary steps from the adversary path."""
    match = re.search("t0-s([0-9]+)-", adversary_path)
    if match:
        return match.group(1)
    else:
        return "UNKNOWN"


def write_bot(
    f: IO[str],
    bot_index: int,
    bot_path: Union[str, Path],
    bot_name: str,
    num_visits: int,
    bot_algorithm: str,
    extra_parameters: Iterable[Mapping[str, str]] = {},
) -> None:
    """Writes bot config parameters to file `f`."""
    use_graph_search = bot_algorithm == "MCTS"
    f.write(
        f"""\
nnModelFile{bot_index} = {bot_path}
botName{bot_index} = {bot_name}
maxVisits{bot_index} = {num_visits}
searchAlgorithm{bot_index} = {bot_algorithm}
useGraphSearch{bot_index} = {str(use_graph_search).lower()}
""",
    )
    for param in extra_parameters:
        f.write(f"{param['key']}{bot_index} = {param['value']}\n")


def write_victims(
    f: IO[str],
    victims: Sequence[Mapping[str, Any]],
    bot_index_offset: int = 0,
) -> None:
    """Writes victim config parameters to file `f`."""
    secondary_bots = ",".join(
        map(lambda x: str(x + bot_index_offset), range(len(victims))),
    )
    f.write(f"secondaryBots = {secondary_bots}\n")
    for i, victim in enumerate(victims):
        f.write("\n")
        write_bot(
            f=f,
            bot_index=bot_index_offset + i,
            bot_path=(
                f"/shared/victims/{victim['filename']}"
                if "path" not in victim
                else victim["path"]
            ),
            bot_name=victim["name"],
            num_visits=victim["visits"],
            bot_algorithm=victim.get("algorithm", "MCTS"),
            extra_parameters=victim.get("extra_parameters", []),
        )


def write_adversaries(
    f: IO[str],
    adversaries: Sequence[Mapping[str, Any]],
    bot_index_offset: int = 0,
) -> None:
    """Writes adversary config parameters to file `f`."""
    secondary_bots_2 = ",".join(
        map(lambda x: str(x + bot_index_offset), range(len(adversaries))),
    )
    f.write(f"secondaryBots2 = {secondary_bots_2}\n")
    for i, adversary in enumerate(adversaries):
        f.write("\n")
        algorithm = adversary["algorithm"]
        path = str(adversary["path"])
        visits = adversary["visits"]
        steps = int(get_adversary_steps(path)) + adversary.get("step_offset", 0)
        write_bot(
            f=f,
            bot_index=bot_index_offset + i,
            bot_path=path,
            bot_name=f"adv-s{steps}-v{visits}-{algorithm}",
            num_visits=visits,
            bot_algorithm=algorithm,
        )


def generate_main_adversary_evaluation(
    parameters: Mapping[str, Any],
    config_dir: Path,
    repo_root: Path,
) -> None:
    """Generates experiment config for main evaluation of adversary."""
    parameters_key = "main_adversary_evaluation"
    if parameters_key not in parameters:
        return
    common_parameters = parameters
    parameters = parameters[parameters_key]

    victims = parameters["victims"]
    num_games = len(victims) * parameters["num_games_per_matchup"]
    output_config = config_dir / "main_adversary_evaluation.cfg"
    usage_string = get_usage_string(
        repo_root=repo_root,
        job_description="evaluate the main adversary against several victims",
        job_name="eval-main-adv",
        default_num_gpus=2,
        num_games=num_games,
        configs=[output_config],
    ).usage_string

    with open(output_config, "w") as f:
        f.write(str_to_comment(usage_string))

        f.write("logSearchInfo = false\n")
        f.write(f"numGamesTotal = {num_games}\n\n")
        f.write(f"numBots = {len(victims) + 1}\n")
        write_victims(f=f, victims=parameters["victims"])
        f.write("\n")

        write_adversaries(
            f=f,
            adversaries=[
                {
                    "algorithm": "AMCTS-S",
                    "path": adjust_nas_path(
                        common_parameters["main_adversary"]["path"],
                    ),
                    "visits": parameters["adversary_visits"],
                },
            ],
            bot_index_offset=len(victims),
        )

    print(f"\n{usage_string}\n")


def generate_training_checkpoint_sweep_evaluation(
    parameters: Mapping[str, Any],
    config_dir: Path,
    repo_root: Path,
) -> None:
    """Generates experiment config for training checkpoint sweep."""
    parameters_key = "training_checkpoint_sweep"
    if parameters_key not in parameters:
        return
    common_parameters = parameters
    parameters = parameters[parameters_key]

    evaluation_config_dir = config_dir / "training_checkpoint_sweep_evaluation"
    evaluation_config_dir.mkdir(parents=True, exist_ok=True)
    victim_config = evaluation_config_dir / "victims.cfg"
    victims = parameters["victims"]
    with open(victim_config, "w") as f:
        f.write("logSearchInfo = false\n")
        # Reduce memory usage of each NN since we have a lot of distinct NNs.
        f.write("nnCacheSizePowerOfTwo = 20\n")
        f.write("nnMutexPoolSizePowerOfTwo = 16\n")
        write_victims(f, victims)

    # Fetch `num_checkpoints_to_evaluate` evenly spaced checkpoints from
    # `checkpoints_paths`.
    checkpoints_paths = parameters["checkpoints_paths"]
    checkpoints = []  # tuple of (path, step_offset)
    natsort_key = natsort.natsort_keygen()
    final_checkpoint = None
    step_offset = 0
    with create_dummy_devbox() as devbox:
        for i, entry in enumerate(checkpoints_paths):
            path = Path(entry["path"]) / "models"
            last_checkpoint_in_path = entry["last_checkpoint"]
            final_checkpoint = (path / last_checkpoint_in_path, step_offset)

            intermediate_checkpoints = [
                checkpoint for checkpoint in devbox.run(f"ls -v {path}").split("\n")
            ]
            if i < len(checkpoints_paths) - 1:
                # For the final path (i == len(checkpoints_paths - 1), we should
                # evaluate checkpoints beyond the final checkpoint to get a
                # complete training curve. Otherwise, we can throw away
                # checkpoints beyond last_checkpoint_in_path.
                intermediate_checkpoints = [
                    checkpoint
                    for checkpoint in intermediate_checkpoints
                    if natsort_key(checkpoint) <= natsort_key(last_checkpoint_in_path)
                ]
            if i > 0 and intermediate_checkpoints[0] == "t0-s0-d0":
                # For any path beyond the first one, t0-s0-d0 is likely a
                # warmstart checkpoint equal to the final checkpoint of the
                # previous path.
                intermediate_checkpoints.pop(0)
            checkpoints.extend(
                (path / checkpoint, step_offset)
                for checkpoint in intermediate_checkpoints
            )
            # All subsequent checkpoints should have their step count
            # incremented.
            step_offset += int(get_adversary_steps(last_checkpoint_in_path))
    indices_to_evaluate = np.unique(
        np.linspace(
            0,
            len(checkpoints) - 1,
            parameters["num_checkpoints_to_evaluate"],
        )
        .round()
        .astype(int),
    )
    checkpoints_to_evaluate = [checkpoints[i] for i in indices_to_evaluate]
    if final_checkpoint not in checkpoints_to_evaluate:
        checkpoints_to_evaluate.append(final_checkpoint)

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
    checkpoints_per_job = parameters.get(
        "checkpoints_per_job", math.floor((16384 * 0.8 - 5942) / 815)
    )
    job_commands = []
    job_description = "evaluate several adversary checkpoints throughout training"
    visits_arr = parameters["adversary_visits"]
    for checkpoints_start in range(
        0,
        len(checkpoints_to_evaluate),
        checkpoints_per_job,
    ):
        checkpoints_end = min(
            checkpoints_start + checkpoints_per_job,
            len(checkpoints_to_evaluate),
        )
        job_name = f"checkpoints-{checkpoints_start}-to-{checkpoints_end}"
        job_config = evaluation_config_dir / f"{job_name}.cfg"

        with open(job_config, "w") as f:
            job_checkpoints = checkpoints_to_evaluate[checkpoints_start:checkpoints_end]
            num_games = (
                len(victims)
                * len(job_checkpoints)
                * len(visits_arr)
                * parameters["num_games_per_matchup"]
            )
            usage_string = get_usage_string(
                repo_root=repo_root,
                job_description=job_description,
                job_name=job_name,
                default_num_gpus=1,
                num_games=num_games,
                configs=[victim_config, job_config],
            )
            f.write(str_to_comment(usage_string.usage_string))
            job_commands.append(usage_string.command)

            f.write(f"numGamesTotal = {num_games}\n")
            f.write(
                f"numBots = {len(victims) + len(job_checkpoints) * len(visits_arr)}\n"
            )
            write_adversaries(
                f=f,
                adversaries=[
                    {
                        "algorithm": parameters["adversary_algorithm"],
                        "path": Path(checkpoint) / "model.bin.gz",
                        "visits": visits,
                        "step_offset": step_offset,
                    }
                    for checkpoint, step_offset in job_checkpoints
                    for visits in visits_arr
                ],
                bot_index_offset=len(victims),
            )

        k8s_config = evaluation_config_dir / f"k8s-{job_name}.yml"
        with open(k8s_config, "w") as f:
            f.write(
                f"""
apiVersion: batch/v1
kind: Job
metadata:
  name: {parameters['job_prefix']}-{job_name}
  labels:
    kueue.x-k8s.io/queue-name: farai
spec:
  suspend: true # The job must start suspended kueue will start it when it is admitted
  template:
    spec:
      priorityClassName: normal-batch
      containers:
      - command:
        - /go_attack/kubernetes/match.sh
        - {parameters['results_dir']}/{job_name}
        - "-1"
        - -config
        - {victim_config.resolve()}
        - -config
        - {job_config.resolve()}
        name: match
        image: humancompatibleai/goattack:{parameters['commit']}-cpp
        resources:
          limits:
            memory: 55Gi
            nvidia.com/gpu: 1
          requests:
            cpu: 1
            nvidia.com/gpu: 1
        volumeMounts:
        - mountPath: /shared
          name: go-attack
      restartPolicy: Never
      volumes:
      - name: go-attack
        persistentVolumeClaim:
          claimName: go-attack"""
            )

    command = "\n".join(job_commands)
    print(f"\nExperiment: {job_description}\nCommand:\n{command}\n")


def generate_katago_ckpt_sweep_evaluation(
    parameters: Mapping[str, Any],
    config_dir: Path,
    repo_root: Path,
    run_on_chai: bool = True,
) -> None:
    """Evaluate our adversary against different KataGo checkpoints."""
    common_parameters = parameters

    parameters_key = "katago_ckpt_sweep"
    if parameters_key not in parameters:
        return
    parameters = parameters[parameters_key]

    def adjust_nas_path_custom(s: str) -> str:
        if run_on_chai:
            return s
        return adjust_nas_path(s)

    def get_drows(s: str) -> int:
        """Get the drows from a checkpoint path.

        Args:
            s: The name of the model
                Accepted formats:
                'kata1-b40c256-s11840935168-d2898845681'
                'kata1-b40c256-s11840935168-d2898845681.bin.gz'
                'kata1-b6c96-s83588096-d12203675.txt.gz'

        Returns:
            The drows of the checkpoint
        """
        return int(s.rstrip(".bin.gz").rstrip(".txt.gz").split("-d")[-1])

    victim_dir = Path(parameters["victim_dir"])
    victim_start_drows: int = get_drows(parameters["victim_start"])

    # Fetch victims from victim_dir newer than victim_start
    victim_paths = victim_dir.glob("*.gz")
    victims: List[str] = [
        p.name
        for p in victim_paths
        if get_drows(p.name) >= victim_start_drows
        and any(sz_str in p.name for sz_str in parameters["net_sizes"])
    ]

    # Sort victims by drows
    victims.sort(key=get_drows)

    evaluation_config_dir = config_dir / "katago_ckpt_sweep_evaluation"
    evaluation_config_dir.mkdir(parents=True, exist_ok=True)

    # Each victim checkpoint costs GPU memory, so we cannot give every
    # checkpoint to a job if the number of checkpoints is high.
    # Instead, we split the checkpoints up among several jobs.
    n_victims_per_gpu: int = parameters["n_victims_per_gpu"]

    # Write adversary config
    adversary_config = evaluation_config_dir / "adversary.cfg"
    with open(adversary_config, "w") as f:
        f.write("logSearchInfo = false\n")
        write_adversaries(
            f=f,
            adversaries=[
                {
                    "path": adjust_nas_path_custom(
                        parameters["adversary_path"]
                        or common_parameters["main_adversary"]["path"],
                    ),
                    "algorithm": parameters["adversary_algorithm"],
                    "visits": parameters["adversary_visits"],
                },
            ],
        )

    # Write victim configs
    job_commands = []
    job_description: str = "evaluate adversary against several KataGo checkpoints"

    victim_visits: list[int] = parameters["victim_visits"]
    victim_x_visits = list(itertools.product(victims, victim_visits))

    for idx_start in range(0, len(victim_x_visits), n_victims_per_gpu):
        idx_end = min(idx_start + n_victims_per_gpu, len(victim_x_visits))
        job_name = f"victims-{idx_start}-to-{idx_end - 1}"
        job_config = evaluation_config_dir / f"{job_name}.cfg"

        with open(job_config, "w") as f:
            job_victim_x_visits = victim_x_visits[idx_start:idx_end]
            num_games = len(job_victim_x_visits) * parameters["num_games_per_matchup"]
            usage_string = get_usage_string(
                repo_root=repo_root,
                job_description=job_description,
                job_name=job_name,
                default_num_gpus=1,
                num_games=num_games,
                configs=[adversary_config, job_config],
            )
            f.write(str_to_comment(usage_string.usage_string))
            job_commands.append(usage_string.command)

            f.write(f"numGamesTotal = {num_games}\n")
            f.write(f"numBots = {len(job_victim_x_visits) + 1}\n")
            write_victims(
                f=f,
                victims=[
                    {
                        "path": adjust_nas_path_custom(str(victim_dir / victim)),
                        "name": victim.lstrip("kata1-").rstrip(".bin.gz")
                        + f"-v{visits}",
                        "visits": visits,
                    }
                    for victim, visits in job_victim_x_visits
                ],
                bot_index_offset=1,
            )

    command = "\n".join(job_commands)
    print(f"\nExperiment: {job_description}\nCommand:\n{command}\n")


def generate_victim_visit_sweep_evaluation(
    parameters: Mapping[str, Any],
    config_dir: Path,
    repo_root: Path,
) -> None:
    """Generates experiment config for sweeping over victim visits."""
    parameters_key = "victim_visit_sweep"
    if parameters_key not in parameters:
        return
    common_parameters = parameters
    parameters = parameters[parameters_key]

    for algorithm_parameters in parameters["adversary_algorithms"]:
        algorithm = algorithm_parameters["algorithm"]
        output_config = config_dir / f"victim-visit-sweep-{algorithm}.cfg"
        max_victim_visits = algorithm_parameters["max_victim_visits"]

        victim_visits = [2 ** i for i in range(int(math.log2(max_victim_visits)))]
        victim_visits.append(max_victim_visits)
        victims = [
            {
                **victim,
                "name": f"{victim['name']}-v{visits}",
                "visits": visits,
            }
            for visits in victim_visits
            for victim in parameters["victims"]
        ]
        num_games = len(victims) * parameters["num_games_per_matchup"]
        # The job name must be lower case and cannot include special characters
        # like "+" in "AMCTS-S++".
        job_name = re.sub("[^0-9a-zA-Z.-]", "x", f"victim-v-sweep-{algorithm}").lower()
        usage_string = get_usage_string(
            repo_root=repo_root,
            job_description=(
                f"evaluate {algorithm} adversary vs. victim with varying victim visits"
            ),
            job_name=job_name,
            default_num_gpus=4,
            num_games=num_games,
            configs=[output_config],
        ).usage_string
        with open(output_config, "w") as f:
            f.write(str_to_comment(usage_string))

            f.write("logSearchInfo = false\n")
            f.write(f"numGamesTotal = {num_games}\n\n")
            f.write(f"numBots = {len(victims) + 1}\n")
            write_victims(f=f, victims=victims)
            f.write("\n")

            write_adversaries(
                f=f,
                adversaries=[
                    {
                        "algorithm": algorithm,
                        "path": adjust_nas_path(
                            common_parameters["main_adversary"]["path"],
                        ),
                        "visits": parameters["adversary_visits"],
                    },
                ],
                bot_index_offset=len(victims),
            )
        print(f"\n{usage_string}\n")


def generate_adversary_visit_sweep_evaluation(
    parameters: Mapping[str, Any],
    config_dir: Path,
    repo_root: Path,
) -> None:
    """Generates experiment config for sweeping over adversary visits."""
    parameters_key = "adversary_visit_sweep"
    if parameters_key not in parameters:
        return
    common_parameters = parameters
    parameters = parameters[parameters_key]

    victims = parameters["victims"]
    max_adversary_visits = parameters["max_adversary_visits"]
    adversary_visits = [2 ** i for i in range(int(math.log2(max_adversary_visits)))]
    adversary_visits.append(max_adversary_visits)
    num_games = (
        len(victims) * len(adversary_visits) * parameters["num_games_per_matchup"]
    )
    output_config = config_dir / "adversary-visit-sweep.cfg"
    usage_string = get_usage_string(
        repo_root=repo_root,
        job_description="evaluate adversary with varying visits vs. victim",
        job_name="adv-v-sweep",
        default_num_gpus=3,
        num_games=num_games,
        configs=[output_config],
    ).usage_string
    with open(output_config, "w") as f:
        f.write(str_to_comment(usage_string))

        f.write("logSearchInfo = false\n")
        f.write(f"numGamesTotal = {num_games}\n\n")
        f.write(f"numBots = {len(adversary_visits) + 1}\n\n")
        write_victims(f=f, victims=victims)
        f.write("\n")
        write_adversaries(
            f=f,
            adversaries=[
                {
                    "algorithm": parameters["adversary_algorithm"],
                    "path": adjust_nas_path(
                        common_parameters["main_adversary"]["path"],
                    ),
                    "visits": visits,
                }
                for visits in adversary_visits
            ],
            bot_index_offset=len(victims),
        )
    print(f"\n{usage_string}\n")


def main():
    """Entrypoint for the script."""
    repo_root = Path(os.path.dirname(os.path.realpath(__file__))).parents[0]

    parser = argparse.ArgumentParser(
        description="Generates config files for the main experiments in paper. "
        "Should be run from a place where /nas/ucb is mounted at /nas/ucb "
        "(e.g. on a CHAI machine or the Hofvarpnir login node).",
    )
    parser.add_argument(
        "parameter_file",
        type=Path,
        help="Path to YAML file providing parameters for the experiments.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="The directory at which to output config files.",
        default=repo_root / "configs" / "generated_evaluations",
    )
    parser.add_argument(
        "--run-on-chai",
        action="store_true",
        help="Generate experiments to run on a CHAI machine "
        "(rnn, gan, dqn, ddpg, gail, etc.). "
        "This flag is not implemented for some experiments.",
    )
    args = parser.parse_args()

    config_dir = args.output_dir
    config_dir.mkdir(parents=True, exist_ok=True)

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
    generate_katago_ckpt_sweep_evaluation(
        evaluation_parameters,
        config_dir=config_dir,
        repo_root=repo_root,
        run_on_chai=args.run_on_chai,
    )
    generate_victim_visit_sweep_evaluation(
        evaluation_parameters,
        config_dir=config_dir,
        repo_root=repo_root,
    )
    generate_adversary_visit_sweep_evaluation(
        evaluation_parameters,
        config_dir=config_dir,
        repo_root=repo_root,
    )


if __name__ == "__main__":
    main()
