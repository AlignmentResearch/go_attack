from dataclasses import dataclass
from typing import List

import dataclasses


@dataclasses.dataclass
class Bot:
    nickname: str
    nn_file: str
    max_visits: int


MODELS_WITH_RANKS = [
    ("kata1-b40c256-s11101799168-d2715431527.bin.gz", "S"),  # 13466.2 ± 18.5
    ("kata1-b20c256x2-s1224669184-d317666228.txt.gz", "A"),  # 12483.2 ± 22.1
    ("kata1-b15c192-s172540416-d88080224.txt.gz", "B"),  # 11492.4 ± 21.6
    ("kata1-b10c128-s61853696-d32291607.txt.gz", "C"),  # 10455.3 ± 22.1
]

BOTS: List[Bot] = []

# Generate bot parameters
for nn_file, rank in MODELS_WITH_RANKS:
    for vpow in range(8):
        BOTS.append(
            Bot(
                nickname=f"bot{rank}-v{2**vpow}",
                nn_file=nn_file,
                max_visits=2**vpow,
            )
        )

# Print config lines
print(f"numBots = {len(BOTS)}")
print()
for idx, bot in enumerate(BOTS):
    print(f"nnModelFile{idx} = /models/{bot.nn_file}")
    print(f"botName{idx} = {bot.nickname}")
    print(f"maxVisits{idx} = {bot.max_visits}")
print()

N_GPUS = 8
N_THREADS_PER_MODEL = 8
assert N_THREADS_PER_MODEL % N_GPUS == 0
for model_idx, _ in enumerate(MODELS_WITH_RANKS):
    for thread_idx in range(N_THREADS_PER_MODEL):
        gpu_idx = thread_idx % N_GPUS
        print(f"cudaDeviceToUseModel{model_idx}Thread{thread_idx} = {gpu_idx}")
