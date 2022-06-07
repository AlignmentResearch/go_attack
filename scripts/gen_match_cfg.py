from dataclasses import dataclass
from typing import List

import dataclasses


@dataclasses.dataclass
class Bot:
    nickname: str
    nn_file: str
    max_visits: int

NUM_GAMES_PER_PAIR: int = 50
MODELS_WITH_NAMES = [
    ("kata1-b20c256x2-s5303129600-d1228401921.bin.gz", "cp127"),  # 12952.1 ± 19.6
    ("kata1-b15c192-s497233664-d149638345.txt.gz", "cp99"),  # 11840.3 ± 22.0
    ("kata1-b10c128-s197428736-d67404019.txt.gz", "cp79"),  # 10998.2 ± 20.3
    ("kata1-b6c96-s175395328-d26788732.txt.gz", "cp63"),  # 10000.3 ± 22.0
    ("kata1-b6c96-s41312768-d6061202.txt.gz", "cp37"),  # 7590.8 ± 22.0
]

BOTS: List[Bot] = []

# Generate bot parameters
for nn_file, name in MODELS_WITH_NAMES:
    for vpow in range(11):
        BOTS.append(
            Bot(
                nickname=f"{name}-v{2**vpow}",
                nn_file=nn_file,
                max_visits=2**vpow,
            )
        )

# Print config lines
print(f"numGamesTotal = {NUM_GAMES_PER_PAIR * len(BOTS) * (len(BOTS) - 1) // 2}")
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
for model_idx, _ in enumerate(MODELS_WITH_NAMES):
    for thread_idx in range(N_THREADS_PER_MODEL):
        gpu_idx = thread_idx % N_GPUS
        print(f"cudaDeviceToUseModel{model_idx}Thread{thread_idx} = {gpu_idx}")
