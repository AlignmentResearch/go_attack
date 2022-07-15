# Uses pynvml to select the index of the least-used GPU with sufficient free memory.
# The `min_free_memory` argument is interpreted in gigabytes
def select_best_gpu(min_free_memory: float) -> int:
    # There's only one GPU available, just
    from torch.cuda import device_count

    if device_count() <= 1:
        return 0

    from pynvml import (
        nvmlInit,
        nvmlDeviceGetCount,
        nvmlDeviceGetHandleByIndex,
        nvmlDeviceGetIndex,
        nvmlDeviceGetMemoryInfo,
        nvmlDeviceGetUtilizationRates,
        nvmlShutdown,
    )
    from time import sleep

    nvmlInit()
    num_gpus = nvmlDeviceGetCount()
    if num_gpus == 1:
        return 0

    handles = [nvmlDeviceGetHandleByIndex(i) for i in range(num_gpus)]
    polling_msg_shown = False
    while True:
        candidates = list(
            filter(
                lambda handle: nvmlDeviceGetMemoryInfo(handle).free
                >= min_free_memory * 1e9,
                handles,
            )
        )
        if not candidates:
            if not polling_msg_shown:
                polling_msg_shown = True
                print(
                    f"No devices are available with at least {min_free_memory} GB of"
                    f"free memory. Polling every 10 sec until a suitable GPU is found."
                )

            sleep(10.0)
        else:
            # After filtering out GPUs that don't have sufficient memory, the "best"
            # one is the one that has the least compute utilization- if there are ties,
            # we use the *amount* of free memory as a tie breaker
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
