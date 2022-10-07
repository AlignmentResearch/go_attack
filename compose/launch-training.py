import os
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path


def get_output_dir(name_prefix: str, parent_dir: Path, *, resume: bool) -> Path:
    # If resuming, find the most recent directory that matches the prefix
    if resume:
        # Find the most recently modified directory that matches the prefix
        full_dir = max(
            (
                d
                for d in parent_dir.iterdir()
                if d.is_dir() and d.name.startswith(name_prefix)
            ),
            key=lambda d: d.stat().st_mtime,
            default=None,
        )
        if full_dir is None:
            raise FileNotFoundError("No matching directories found")

        print(f"Resuming training from {full_dir}")

    # Create a new directory for this training run
    else:
        timestamp = datetime.now().strftime("%F-%T")
        run_name = f"{name_prefix}_{timestamp}"
        full_dir = parent_dir / run_name

        # Should basically never happen because we use seconds in the timestamp
        if full_dir.exists():
            raise FileExistsError(f"Bizarrely, directory {full_dir} already exists.")

        print(f"Starting run with name: {run_name}")

    return full_dir


def build_victimplay_cmd(config_path: Path, num_gpus: int, *, debug: bool) -> str:
    victimplay_args = f"""\
    victimplay \
    -output-dir /outputs/selfplay \
    -models-dir /outputs/models \
    -nn-victim-path /outputs/victims \
    -config {config_path} \
    -config /configs/compute/{num_gpus}gpu.cfg \
    """

    if debug:
        return f"gdb ./cpp/katago --ex 'set args{victimplay_args}' --ex 'catch throw'"
    else:
        return f"./cpp/katago {victimplay_args}"


def build_docker_compose_cmd(
    output_dir: Path, victimplay_cmd: str, *, fast: bool, service: str
) -> str:
    # Be robust to being run from any directory
    this_script_path = Path(__file__).resolve()
    compose_dir = this_script_path.parent
    go_attack_dir = compose_dir.parent

    host_victims_dir = go_attack_dir / "victim-models"
    if host_victims_dir.exists():
        print(f"Using victim models from: {host_victims_dir}")
    else:
        raise FileNotFoundError(
            f"Please create a directory for victim models at: {host_victims_dir}"
        )

    if service:
        docker_cmd = f"run {service}"
        print(f"Only running the {service} service")
    else:
        print("Running all services")
        docker_cmd = "up"

    return f"""
    HOST_OUTPUT_DIR={output_dir} \
    HOST_VICTIMS_DIR={host_victims_dir} \
    NAMEOFRUN={output_dir.name} \
    VICTIMPLAY_CMD="{victimplay_cmd}" \
    docker-compose \
    -f {compose_dir}/victimplay.yml \
    --env-file {compose_dir}/{'victimplay-debug' if fast else 'victimplay'}.env \
    {docker_cmd}
    """


def main():
    parser = ArgumentParser(description="Launch a victimplay training job")
    parser.add_argument(
        "name_prefix",
        type=str,
        help="Prefix for this training run. Will be concatenated with a timestamp.",
    )
    parser.add_argument(
        "--config", "-c", type=Path, default="/configs/active-experiment.cfg"
    )
    parser.add_argument(
        "--fast", action="store_true", help="Use fast 'victimplay-debug.env' config"
    )
    parser.add_argument(
        "--gpus",
        "-g",
        type=int,
        default=7,
        help="Number of GPUs to use for the victimplay service",
    )
    parser.add_argument(
        "--debug", "-d", action="store_true", help="Run victimplay in GDB"
    )
    parser.add_argument(
        "--parent-dir",
        "-p",
        type=Path,
        help="Directory for data, models, and logs. Defaults to /nas/ucb/$(whoami).",
    )
    parser.add_argument(
        "--resume",
        "-r",
        action="store_true",
        help="Resume training from last checkpoint",
    )
    parser.add_argument(
        "--service",
        "-s",
        type=str,
        help="Specify a service to run, otherwise will run all services",
    )
    args = parser.parse_args()

    # If the parent directory is not specified, use the user's home directory on the NAS
    if not args.parent_dir:
        args.parent_dir = Path("/nas/ucb/") / os.getlogin()

    output_dir = get_output_dir(args.name_prefix, args.parent_dir, resume=args.resume)
    output_dir.mkdir(exist_ok=True, parents=True)

    victimplay_cmd = build_victimplay_cmd(args.config, args.gpus, debug=args.debug)
    docker_compose_cmd = build_docker_compose_cmd(
        output_dir,
        victimplay_cmd,
        fast=args.fast,
        service=args.service,
    )

    print(f"Running command: {docker_compose_cmd}")
    os.system(docker_compose_cmd)


if __name__ == "__main__":
    main()
