import os
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path


def main():
    parser = ArgumentParser(description="Launch a victimplay training job")
    parser.add_argument(
        "name_prefix",
        type=str,
        help="Prefix for this training run. Will be concatenated with a timestamp.",
    )
    parser.add_argument(
        "--config", "-c", type=str, default="/configs/active-experiment.cfg"
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

    # If resuming, find the most recent directory that matches the prefix
    if args.resume:
        # Find the most recently modified directory that matches the prefix
        full_dir = max(
            (
                d
                for d in args.parent_dir.iterdir()
                if d.is_dir() and d.name.startswith(args.name_prefix)
            ),
            key=lambda d: d.stat().st_mtime,
            default=None,
        )
        assert full_dir is not None, "No matching directories found"

        print(f"Resuming training from {full_dir}")

    # Create a new directory for this training run
    else:
        timestamp = datetime.now().strftime("%F-%T")
        run_name = f"{args.name_prefix}_{timestamp}"
        full_dir = args.parent_dir / run_name
        print(f"Starting run with name: {run_name}")

        if full_dir.exists():
            print(f"Bizarrely, directory {full_dir} already exists. Exiting.")
            exit(1)

    victimplay_args = f"""\
    victimplay \
    -output-dir /outputs/selfplay \
    -models-dir /outputs/models \
    -nn-victim-path /outputs/victims \
    -config {args.config} \
    -config /configs/compute/{args.gpus}gpu.cfg \
    """

    if args.debug:
        victimplay_cmd = (
            f"gdb ./cpp/katago --ex 'set args{victimplay_args}' --ex 'catch throw'"
        )
    else:
        victimplay_cmd = f"./cpp/katago {victimplay_args}"

    full_dir.mkdir(exist_ok=True, parents=True)

    # Be robust to being run from any directory
    this_script_path = Path(__file__).resolve()
    compose_dir = this_script_path.parent
    go_attack_dir = compose_dir.parent

    host_victims_dir = go_attack_dir / "victim-models"
    if host_victims_dir.exists():
        print(f"Using victim models from: {host_victims_dir}")
    else:
        print(f"Please create a directory for victim models at: {host_victims_dir}")
        exit(1)

    if args.service:
        docker_cmd = f"run {args.service}"
        print(f"Only running the {args.service} service")
    else:
        print("Running all services")
        docker_cmd = "up"

    os.system(
        f"""
    HOST_OUTPUT_DIR={full_dir} \
    HOST_VICTIMS_DIR={host_victims_dir} \
    NAMEOFRUN={full_dir.name} \
    VICTIMPLAY_CMD="{victimplay_cmd}" \
    docker-compose \
    -f {compose_dir}/victimplay.yml \
    --env-file {compose_dir}/{'victimplay-debug' if args.fast else 'victimplay'}.env \
    {docker_cmd}
    """
    )


if __name__ == "__main__":
    main()
