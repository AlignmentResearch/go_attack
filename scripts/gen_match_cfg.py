"""Generates match config to play KataGo networks against each other."""

import dataclasses
from typing import List


@dataclasses.dataclass
class Bot:
    """Bot config."""

    nickname: str
    nn_file: str
    max_visits: int


MODELS_WITH_NAMES = [
    (
        "/garoot/training/emcts1-curr/cp127-to-505-v1/models/t0-s34090496-d8262123/model.bin.gz",
        "adv-s34090496",
    ),
    (
        "/garoot/training/emcts1-curr/cp127-to-505-v1/models/t0-s59042304-d14514443/model.bin.gz",
        "adv-s59042304",
    ),
]

N_GPUS = 8
N_THREADS_PER_MODEL = 8


def main():
    """Main entrypoint to generate match config."""
    bots: List[Bot] = []

    # Generate bot parameters
    for nn_file, name in MODELS_WITH_NAMES:
        for visits in sorted(list(set([2**_ for _ in range(11)] + [600]))):
            bots.append(
                Bot(
                    nickname=f"{name}-v{visits}",
                    nn_file=nn_file,
                    max_visits=visits,
                ),
            )

    # Print config lines
    print(f"numBots = {len(bots)}")
    print()
    for idx, bot in enumerate(bots):
        print(f"nnModelFile{idx} = {bot.nn_file}")
        print(f"botName{idx} = {bot.nickname}")
        print(f"maxVisits{idx} = {bot.max_visits}")
        print(f"searchAlgorithm{idx} = EMCTS1")
        print(f"EMCTS1_noiseOppNodes{idx} = true")
        print()
    print()

    assert N_THREADS_PER_MODEL % N_GPUS == 0
    for model_idx, _ in enumerate(MODELS_WITH_NAMES):
        for thread_idx in range(N_THREADS_PER_MODEL):
            gpu_idx = thread_idx % N_GPUS
            print(f"cudaDeviceToUseModel{model_idx}Thread{thread_idx} = {gpu_idx}")


if __name__ == "__main__":
    main()
