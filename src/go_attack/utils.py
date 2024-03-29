"""Miscellaneous utility functions."""

import ast
import re
from pathlib import Path
from time import sleep
from typing import Any, List, Mapping, Optional

from pynvml import (
    nvmlDeviceGetCount,
    nvmlDeviceGetHandleByIndex,
    nvmlDeviceGetIndex,
    nvmlDeviceGetMemoryInfo,
    nvmlDeviceGetUtilizationRates,
    nvmlInit,
    nvmlShutdown,
)


def select_best_gpu(min_free_memory: float) -> int:
    """Use pynvml to find index of the least-used GPU with enough free memory.

    Args:
        min_free_memory: The minimum amount of free memory in gigabytes

    Returns:
        The index of a GPU with at least `min_free_memory` gigabytes of free
        memory. Among the GPUs with sufficient free memory, the least-used one
        is selected.
    """
    nvmlInit()
    num_gpus = nvmlDeviceGetCount()
    if num_gpus == 1:
        return 0

    handles = [nvmlDeviceGetHandleByIndex(i) for i in range(num_gpus)]
    polling_msg_shown = False
    while True:
        candidates = [
            handle
            for handle in handles
            if nvmlDeviceGetMemoryInfo(handle).free >= min_free_memory * 1e9
        ]
        if not candidates:
            if not polling_msg_shown:
                polling_msg_shown = True
                print(
                    f"No devices are available with at least {min_free_memory}"
                    f" GB of free memory. Polling every 10 sec until a "
                    f"suitable GPU is found.",
                )

            sleep(10.0)
        else:
            # After filtering out GPUs that don't have sufficient memory, the
            # "best" one is the one that has the least compute utilization- if
            # there are ties, we use the amount of free memory as a tiebreaker
            best = min(
                candidates,
                key=lambda handle: (
                    nvmlDeviceGetUtilizationRates(handle).gpu,
                    -nvmlDeviceGetMemoryInfo(handle).free,
                ),
            )

            best_idx = nvmlDeviceGetIndex(best)
            print(f"Selected GPU {best_idx}.")
            nvmlShutdown()
            return best_idx


def _standardize_config(path: Path, include_path: Optional[Path] = None) -> List[str]:
    include_regex = re.compile(r"@include (.+\.cfg)")
    lines = [line.strip() for line in path.open()]

    for i, line in enumerate(lines):
        # Remove comments
        comment_idx = line.find("#")
        if comment_idx != -1:
            line = line[:comment_idx]

        # Flatten the include directives
        if match := include_regex.fullmatch(line):
            lines[i : i + 1] = _standardize_config(  # noqa: E203
                (include_path or path.parent) / match[1],
                include_path,
            )
        else:
            lines[i] = line.strip()

    return [line for line in lines if line]


def parse_config(path: Path, include_path: Optional[Path] = None) -> Mapping[str, Any]:
    """Parse a KataGo config file into a dict.

    Args:
        path: Path to the config file.
        include_path: Path to use for resolving @include statements.

    Returns:
        A dict representing the config file.
    """
    standardized = _standardize_config(path, include_path)

    config = {}
    for line in standardized:
        key, value = line.split("=", maxsplit=1)
        value = value.strip()

        # Special case to handle boolean values
        if value in ("true", "false"):
            value = value.capitalize()

        # Try to parse as bool, float, int, or tuple
        try:
            value = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            pass  # Keep the string value

        config[key.strip()] = value

    return config
