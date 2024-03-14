import random

MODELS_PER_CONFIG = 7
NUM_GAMES_PER_PAIR = 10

index = 0
models = []
with open("all-advs.txt") as f:
    for line in f:
        models.append(tuple(line.split()))
assert len(models) == 108

def get_config_common_params(num_bots):
    num_games = (num_bots * (num_bots - 1) // 2) * NUM_GAMES_PER_PAIR
    return f"""numGamesTotal = {num_games}
numBots = {len(config_models)}
nnCacheSizePowerOfTwo = 20
nnMutexPoolSizePowerOfTwo = 16

allowResignation = true
resignConsecTurns = 3
resignThreshold = -0.90
searchFactorAfterOnePass = 0.50
searchFactorAfterTwoPass = 0.25
searchFactorWhenWinning = 0.40
searchFactorWhenWinningThreshold = 0.95

"""


def model_to_bot(path, name, visits, bot_index):
    return f"""nnModelFile{bot_index} = {path}
botName{bot_index} = {name}
maxVisits{bot_index} = {visits}
searchAlgorithm{bot_index} = MCTS
useGraphSearch{bot_index} = true
"""


def write_config(config_path, config_models):
    with open(config_path, "w") as f:
        f.write(get_config_common_params(len(config_models)))
        for j, model in enumerate(config_models):
            f.write(model_to_bot(*model, j))
            f.write("\n")


# first 105 models are ViT/b10, last 3 models are cp79
config_idx = 0
for i in range(0, 105, MODELS_PER_CONFIG):
    config_models = models[i : i + MODELS_PER_CONFIG]
    path = f"configs/{config_idx}.cfg"
    write_config(path, config_models)
    config_idx += 1

while config_idx < 1000:
    config_models = []
    for _ in range(MODELS_PER_CONFIG):
        config_models.append(random.choice(models))
    path = f"configs/{config_idx}.cfg"
    write_config(path, config_models)
    config_idx += 1
