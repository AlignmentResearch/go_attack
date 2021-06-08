import os 
from os.path import join as joinpath
import re
import json
import copy
import pickle
import datetime
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

# getting dict from json file path
def json2dict(json_p):
    with open(json_p, "r") as file_p:
        all = json.load(file_p)
    return all

def dict2df(all, record_keys):
    record_dict = {key : [] for key in record_keys}
    # all = sorted(all, key=lambda x: int(x))
    for k, v in all.items():
        moveWinProb_list = np.array([item["whiteWinProb"] for item in v])
        assert len(set(moveWinProb_list)) <= 8
        record_dict["whiteWinProbMean"].append(moveWinProb_list.mean())
        record_dict["whiteWinProbMax"].append(moveWinProb_list.max())
        record_dict["whiteWinProbMin"].append(moveWinProb_list.min())
        record_dict["whiteWinProbStd"].append(moveWinProb_list.std())
    df_p = pd.DataFrame.from_dict(record_dict)
    df_p.index = [int(x) for x in all.keys()]
    return df_p

def plot_ax(df, plot_keys, ax, **kwargs):
    for key in plot_keys:
        if key == "nnwhiteWinProbRange":
            ax.fill_between(list(df.index), 
            df["whiteWinProbMin"], df["whiteWinProbMax"], alpha=0.2)
        else:
            ax = df[key[2:]].plot(ax=ax, ylim=[-0.1,1.1], label=key)
    
    ax.legend(fontsize=14)
    ax.set_title(kwargs['title'], fontsize = 18)
    if 'yticks' in kwargs.keys():
        ax.set_yticks(kwargs['yticks'])
    ax.grid(True, linestyle='--', alpha=0.3)


if __name__ == "__main__":
    root = str(Path("..").resolve())
    sgf_dir = str(Path(root) / "sgf4test")

    record_keys = ["whiteWinProbMean", "whiteWinProbMax", "whiteWinProbMin", "whiteWinProbStd"]
    plot_keys = ["nnwhiteWinProbMean", "nnwhiteWinProbRange", "nnwhiteWinProbStd"]

    json_file_list = list(filter(lambda x: x.endswith(".json"), os.listdir(sgf_dir)))
    num_json = len(json_file_list)

    fig_game, ax_game = plt.subplots(ncols=num_json, nrows=1, figsize=(num_json*8*1.5, 6*1.5))

    for idx, file in enumerate(json_file_list):
        filepath = str(Path(sgf_dir) / file)
        all = json2dict(filepath)
        df = dict2df(all, record_keys)

        yticks = np.arange(-0.1, 1.1, 0.1)
        ax_game_sub = ax_game[idx]            
        plot_ax(df, plot_keys, ax=ax_game_sub, yticks=yticks, title=file)
    
    # plot each game
    fig_game.savefig(str(Path(sgf_dir) / "sgf4test") + '.png', format='png')
    plt.close()

