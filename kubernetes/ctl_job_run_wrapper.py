"""Wraps ctl to enable launching with ctl or docker."""

import dataclasses
import subprocess
from typing import List, Optional, Tuple

import docker
import docker.types
import simple_parsing
from simple_parsing.wrappers.field_wrapper import DashVariant


@dataclasses.dataclass
class CtlWrapperArgs:
    """Arguments for the ctl wrapper."""

    name: str

    container: Tuple[str, ...]
    command: Tuple[str, ...]
    gpu: Tuple[int, ...]
    replicas: Tuple[int, ...]

    # Volume flags
    shared_host_dir: str
    shared_host_dir_mount: str
    shared_host_dir_slow_tolerant: bool = False

    # High priority flag
    high_priority: bool = False

    # Wrapper only flags
    local_run: bool = False  # Run locally using docker instead of using ctl
    gpu_collo_allowed: Optional[
        Tuple[int, ...]
    ] = None  # Which commands can be placed on the same GPU

    # TODO: Implement a flag to specify which GPUs are available

    def __post_init__(self):
        """Check parsed arguments."""
        assert (
            len(self.container)
            == len(self.command)
            == len(self.gpu)
            == len(self.replicas)
        ), "All lists must be the same length"

        if self.gpu_collo_allowed is not None:
            assert len(self.gpu_collo_allowed) == len(self.gpu)
            assert all(x in [0, 1] for x in self.gpu_collo_allowed)

    def launch(self):
        """Launches the job."""
        if self.local_run:
            self.launch_local()
        else:
            self.launch_ctl()

    def launch_ctl(self):
        """Launches the job using ctl."""
        args = [
            "ctl",
            "job",
            "run",
            "--name",
            self.name[-38:],  # Limit job name to 38 characters for DNS reasons
            "--shared-host-dir",
            self.shared_host_dir,
            "--shared-host-dir-mount",
            self.shared_host_dir_mount,
        ]

        if self.shared_host_dir_slow_tolerant:
            args.append("--shared-host-dir-slow-tolerant")
        if self.high_priority:
            args.append("--high-priority")

        args.extend(("--container",) + self.container)
        args.extend(("--command",) + self.command)
        args.extend(("--gpu",) + tuple(str(x) for x in self.gpu))
        args.extend(("--replicas",) + tuple(str(x) for x in self.replicas))

        subprocess.run(args)

    def get_gpu_indices(self) -> List[List[int]]:
        """Returns a list of gpu indices for each command.

        Commands are duplicated as specified by replicas.

        Returns:
            List of gpu indices for each command.
        """
        gpu_indices: List[List[int]] = []
        min_unused_idx: int = 0
        collo_idx: int = -1
        for job_gpus, job_replicas, collo_allowed in zip(
            self.gpu,
            self.replicas,
            self.gpu_collo_allowed or [0] * len(self.gpu),
        ):
            for _ in range(job_replicas):
                if job_gpus == 0:
                    gpu_indices.append([])
                elif collo_allowed == 1:
                    assert job_gpus == 1
                    assert job_replicas == 1
                    if collo_idx == -1:
                        collo_idx = min_unused_idx
                    gpu_indices.append([collo_idx])
                    min_unused_idx += 1
                else:
                    gpu_indices.append(
                        list(range(min_unused_idx, min_unused_idx + job_gpus)),
                    )
                    min_unused_idx += job_gpus

        return gpu_indices

    def launch_local(self):
        """Launches a job using docker."""
        client = docker.from_env()  # Get docker client

        # Launch the jobs!
        gpu_indices = self.get_gpu_indices()
        job_idx: int = 0
        for container, command, replicas in zip(
            self.container,
            self.command,
            self.replicas,
        ):
            for ridx in range(replicas):
                job_gpu_indices = gpu_indices[job_idx]
                print(
                    f"Launching (replica {ridx + 1}/{replicas}) {container}",
                    f"with command '{command}'",
                    f"on GPU(s) {job_gpu_indices}",
                )

                client.containers.run(
                    image=container,
                    command=command,
                    detach=True,
                    # Volumes
                    volumes={
                        self.shared_host_dir: {
                            "bind": self.shared_host_dir_mount,
                            "mode": "rw",
                        },
                    },
                    # GPU settings
                    device_requests=[
                        docker.types.DeviceRequest(
                            driver="nvidia",
                            capabilities=[["gpu"]],
                            device_ids=[str(x) for x in job_gpu_indices],
                        ),
                    ]
                    if job_gpu_indices != []
                    else None,
                )

                job_idx += 1


if __name__ == "__main__":
    parser = simple_parsing.ArgumentParser(
        add_option_string_dash_variants=DashVariant.DASH,
    )
    parser.add_arguments(CtlWrapperArgs, dest="ctl_wrapper_args")
    ctl_wrapper_args: CtlWrapperArgs = parser.parse_args().ctl_wrapper_args

    ctl_wrapper_args.launch()
