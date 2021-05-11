import os 
import re
import json
import copy
import pickle
import datetime
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

# tools
def get_list(moveInfos, key):
    return [v[key] for k,v in moveInfos.items()]

def get_stats(move_dict, key_list):
    stat_list = []
    for key in key_list:
        if key == 'move':
            stat = move_dict[key]
        elif key == "movePrior":
            move = move_dict['move']
            children_dict = move_dict['Root']['moveInfos']
            movePrior = children_dict[move]['prior']
            stat = movePrior
        elif key == "moveAttackValue":
            move = move_dict['move']
            children_dict = move_dict['Root']['moveInfos']
            moveAttackValue = 1.0-children_dict[move]['effectiveWinValue']
            child_attack_values = dict([(k, 1.0-v['effectiveWinValue']) for k, v in children_dict.items()])
            assert moveAttackValue == child_attack_values[move]
            stat = moveAttackValue
        elif key == "attack?":
            stat = True if children_dict[move]['order'] != 0 else False
        else:
            stat = move_dict['Root'][key]
        stat_list.append(stat)
    return stat_list

def get_game_results(game_data_pth):
    ret = dict()
    with open(game_data_pth, "r") as gd:
        lines = gd.readlines()
    headerIdx = None
    for idx, line in enumerate(lines):
        if '#GAME\tRES_B\tRES_W\tRES_R' in line:
            headerIdx = idx
            break
    for line in lines[headerIdx+1:]:
        line_list = line.split("\t")
        game_idx = int(line_list[0])
        game_out = line_list[1]
        game_moves = int(line_list[6])
        ret[game_idx] = (game_out, game_moves)
    return ret

# getting dict from json file path
def json2dict(json_p):
    with open(json_p, "r") as file_p:
        all_p = json.load(file_p)
    keys_p = sorted(list(all_p.keys()), key=lambda s: int(s.split('-')[-1]))
    return all_p, keys_p

# getting dataframe from dict
def dict2df(all_p, keys_p, record_keys):
    data_p = dict()
    for k in keys_p:
        key = int(k.split('-')[-1])
        data_p[key] = get_stats(all_p[k], record_keys)
    df_p = pd.DataFrame.from_dict(data_p, orient='index', columns=record_keys)
    return df_p

# load json files & preprocess
def preprocess(dic):
    tmp_dic = copy.deepcopy(dic)
    if 'moveInfos' in tmp_dic.keys() and isinstance(tmp_dic['moveInfos'], list):
        if len(tmp_dic['moveInfos']) == 0:
            tmp_dic['moveInfos'] = dict()
            return tmp_dic
        new = dict()
        for m in tmp_dic['moveInfos']:
            assert len(m) == 1
            k = list(m.keys())[0]
            v = preprocess(m[k])
            new[k] = v
        tmp_dic['moveInfos'] = new
    return tmp_dic

def get_preprocessed_all_p(json_p):
    all_p, keys_p = json2dict(json_p)
    # preprocess is a must
    for key in keys_p:
        all_p[key]['Root'] = preprocess(all_p[key]['Root'])
    return all_p, keys_p

# Sanity check
def check_num_children(node_dict):
    assert len(node_dict['moveInfos']) == node_dict['numChildren']
    
def check_value_cal(node_dict):
    root_attackValue = node_dict['attackValue']
    root_effectiveWinValue = node_dict['effectiveWinValue']
    root_minimaxValue = node_dict['minimaxValue']
    
    # get next layer of values
    child_attackValue_list = get_list(node_dict['moveInfos'], 'attackValue')
    child_effectiveWinValue_list = get_list(node_dict['moveInfos'], 'effectiveWinValue')
    child_minimaxValue_list = get_list(node_dict['moveInfos'], 'minimaxValue')
    
    regular_move = list(node_dict['moveInfos'].keys())[0]
    
    assert(root_effectiveWinValue == 1.0 - node_dict['moveInfos'][regular_move]['attackValue'])
    assert(root_attackValue == 1.0 - min(child_effectiveWinValue_list))
    assert(root_minimaxValue == 1.0 - min(child_minimaxValue_list))
    
def sanity_check(keys_p, all_p):
    for key in keys_p:
        move_dict = all_p[key]
        move = move_dict['move']
        node_dict = move_dict['Root']
        check_num_children(node_dict)
        check_value_cal(node_dict)
        
# plot_one_exp from a json filepath
def plot_one_exp(df_p, plot_keys, ax, **kwargs):
    ax = df_p[plot_keys].plot(ax=ax, ylim=[-0.1,1.1], **kwargs)
    ax.legend(fontsize=14)
    ax.set_title(kwargs['title'], fontsize = 18)
#     np.arange(-1.21, -0.79, 0.04)
    ax.set_yticks(np.arange(-0.1, 1.1, 0.1))
    ax.grid(True, linestyle='--', alpha=0.3)


def main(exp_dir, record_key_dict, plot_key_dict):
    print(f"-------- Plotting {exp_dir} --------")
    data_dir = str(Path(exp_dir) / "data_logs")
    plot_dir = str(Path(exp_dir) / "plots")
    os.makedirs(plot_dir, exist_ok=True)
    game_data_pth = str(Path(exp_dir) / "game.dat")

    game_result_dict = get_game_results(game_data_pth)
    
    json_list = os.listdir(data_dir)
    numFinishedGames = len(game_result_dict)
    print(len(json_list), numFinishedGames)

    # save dataframe for each game to pickle files
    for gameIdx in range(numFinishedGames):
        assert f"game-{gameIdx}-Black.json" in json_list, f"Error: game-{gameIdx}-Black.json not in json_list"
        assert f"game-{gameIdx}-White.json" in json_list, f"Error: game-{gameIdx}-White.json not in json_list"

        gameOutcome = game_result_dict[gameIdx][0]
        for idx, player in enumerate(["Black", "White"]):
            pklName = f"game-{gameIdx}-{player}.pkl"
            savePath = str(Path(data_dir) / pklName)
            if pklName in json_list:
                pass
            else:
                plot_keys_p = plot_key_dict[player]
                json_p = str(Path(data_dir) / f"game-{gameIdx}-{player}.json")
                all_p, keys_p = get_preprocessed_all_p(json_p)
                df_p = dict2df(all_p, keys_p, record_key_dict[player])
                if 'scoreStdev/25' in plot_keys_p:
                    df_p['scoreStdev/25'] = df_p['scoreStdev'] / 25 
                df_p.to_pickle(savePath)
                print(f"{pklName} saved!")
            
    # subplots arguments
    twoD = True if numFinishedGames > 1 else False
    ncols = 2 
    nrows = numFinishedGames*2 // ncols if twoD else 1

    fig_all, ax_all = plt.subplots(ncols=ncols, nrows=nrows, figsize=(ncols*8*1.5, nrows*6*1.5))

    # for each game
    for gameIdx in range(numFinishedGames):
        fig_game, ax_game = plt.subplots(ncols=ncols, nrows=1, figsize=(ncols*8*1.5, 1*6*1.5))
        gameOutcome = game_result_dict[gameIdx][0]
        attackMoveNums = None
        for idx, player in enumerate(["Black", "White"]):
            pklName = f"game-{gameIdx}-{player}.pkl"
            savePath = str(Path(data_dir) / pklName)
            plot_keys_p = plot_key_dict[player]
            ax_all_sub = ax_all[gameIdx, idx] if twoD else ax_all[idx]
            ax_game_sub = ax_game[idx]
            with open(savePath, "rb") as file:
                df_p = pickle.load(file)
                print(f"{pklName} loaded!")
            
            plot_one_exp(df_p, plot_keys_p, ax_all_sub, title=f"game-{gameIdx}-{player}.json ({gameOutcome})")
            plot_one_exp(df_p, plot_keys_p, ax_game_sub, title=f"game-{gameIdx}-{player}.json ({gameOutcome})")
            
            # plot attack positions
            if "attack?" in plot_keys_p:
                if player == "Black":
                    attackMoveNums = df_p.index[df_p["attack?"]]
                for xc in attackMoveNums:
                    ax_all_sub.axvline(x=xc, c="red", alpha=0.4)
                    ax_game_sub.axvline(x=xc, c="red", alpha=0.4)
        gamePlotName = f"game-{gameIdx}.jpg"
        fig_game.savefig(str(Path(plot_dir) / gamePlotName), dpi=100, format='jpg')
        print(f"{gamePlotName} plot finished ... ")
        fig_game.clear()

    now = datetime.datetime.now()
    allPlotName = "all_plots"
    print(f"{allPlotName} plot finished ... ")
    fig_all.savefig(str(Path(plot_dir) / allPlotName) + ".jpg", dpi=100, format='jpg')
    # fig.savefig(str(Path(plot_dir) / plot_name) + '.pdf', format='pdf')
    # plt.show()
    plt.close()

if __name__ == "__main__":

    # set record_keys
    record_keys = ['move', 'visits']
    record_keys += ['attackValue', 'effectiveWinValue', 'minimaxValue']
    record_keys += ['winrate', 'winValueAvg(black)', 'winValueAvg(white)']
    record_keys += ['numChildren', 'perspective']
    record_keys += ['scoreLead', 'scoreStdev', 'utility', 'weightSum']
    record_keys += ['moveAttackValue', 'attack?']
    record_keys += ['movePrior']
    record_key_dict = {
        "Black" : copy.copy(record_keys),
        "White" : copy.copy(record_keys)
    }

    # set plot_keys
    plot_key_dict = {
        "Black" : ['winrate', 'attackValue', 'moveAttackValue', 'minimaxValue', "attack?", 'scoreStdev/25'],
        "White" : ['winrate', 'effectiveWinValue', 'minimaxValue', "attack?", 'scoreStdev/25'],
    }
    record_key_dict["Black"] += ['attackUtility', 'effectiveUtility', 'minimaxUtility']
    plot_key_dict["Black"] += ['attackUtility']
    root = str(Path("..").resolve())
    games_dir = str(Path(root) / "games")
    folder_strs = [
        "atkexpand",
        "baseline",
        "mctssb_atkexpand",
        "minimaxsb_atkexpand",
        "softatk",
        "softatk_atkexpand"
    ]
    for fs in folder_strs:
        exp_strs = os.listdir(games_dir + "/" + fs)
        print(exp_strs)
        exp_dirs = list(map(lambda exp_str: str(Path(games_dir) / fs / exp_str), exp_strs))

        for exp_dir in exp_dirs:
            filelist = os.listdir(exp_dir)
            if "game.dat" in filelist:
                main(exp_dir, record_key_dict, plot_key_dict)
            else:
                pass
            if "finished_exp.txt" in exp_dir:
                continue
            