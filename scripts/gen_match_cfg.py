"""Generates match config to play KataGo networks against each other."""

import dataclasses
from typing import List


@dataclasses.dataclass
class Bot:
    """Bot config."""

    nickname: str
    nn_file: str
    max_visits: int


MODELS_WITH_RANKS = [
    # ("kata1-b15c192-s1503689216-d402723070.txt.gz", "cp103"),
    ("kata1-b40c256-s11840935168-d2898845681.bin.gz", "cp505"),
    # ("kata1-b20c256x2-s5303129600-d1228401921.bin.gz", "cp127"),
]

N_GPUS = 8
N_THREADS_PER_MODEL = 8


def main():
    """Main entrypoint to generate match config."""
    bots: List[Bot] = []

    # Generate bot parameters
    for nn_file, bot_name in MODELS_WITH_RANKS:
        for vpow in range(12):
            bots.append(
                Bot(
                    nickname=f"{bot_name}-v{2**vpow}",
                    nn_file=nn_file,
                    max_visits=2**vpow,
                ),
            )

    # Print config lines
    print(f"numBots = {len(bots)}")
    print()
    for idx, bot in enumerate(bots):
        print(f"nnModelFile{idx} = /models/{bot.nn_file}")
        print(f"botName{idx} = {bot.nickname}")
        print(f"maxVisits{idx} = {bot.max_visits}")
        print(f"searchAlgorithm{idx} = MCTS")
        print()
    print()

    assert N_THREADS_PER_MODEL % N_GPUS == 0
    for model_idx, _ in enumerate(MODELS_WITH_RANKS):
        for thread_idx in range(N_THREADS_PER_MODEL):
            gpu_idx = thread_idx % N_GPUS
            print(f"cudaDeviceToUseModel{model_idx}Thread{thread_idx} = {gpu_idx}")


if __name__ == "__main__":
    main()
