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

# tools
def get_list(moveInfos, key):
    return [v[key] for k,v in moveInfos.items()]

def get_stats(move_dict, key_list, player):
    stat_list = []
    for key in key_list:
        move = move_dict['move']
        children_dict = move_dict['Root']['moveInfos']
        child_winrates = dict([(k, 1.0-v['winrate']) for k, v in children_dict.items()])
        child_attack_values = dict([(k, 1.0-v['effectiveWinValue']) for k, v in children_dict.items()])

        if key == 'move':
            stat = move
        elif key == "movePrior":
            movePrior = children_dict[move]['prior']
            stat = movePrior
        elif key == "moveAttackValue":
            moveAttackValue = 1.0-children_dict[move]['effectiveWinValue']
            assert moveAttackValue == child_attack_values[move]
            stat = moveAttackValue
        elif key == "maxChildAttackValue":
            stat = max(child_attack_values.values())
        elif key == "minChildAttackValue":
            stat = min(child_attack_values.values())
        elif key == "childAttackValueStd":
            stat = np.std(list(child_attack_values.values()))

        elif key == "nnWinValue":
            stat = move_dict['Root']["nnWinValue(white)"] if player == "White" else 1.0 - move_dict['Root']["nnWinValue(white)"]

        elif key == "moveWinrate":
            moveWinrate = 1.0-children_dict[move]['winrate']
            assert moveWinrate == child_winrates[move]
            stat = moveWinrate
        elif key == "maxChildWinrate":
            stat = max(child_winrates.values())
        elif key == "minChildWinrate":
            stat = min(child_winrates.values())
        elif key == "childWinrateStd":
            stat = np.std(list(child_winrates.values()))

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
def dict2df(all_p, keys_p, record_keys, player):
    data_p = dict()
    for k in keys_p:
        key = int(k.split('-')[-1])
        data_p[key] = get_stats(all_p[k], record_keys, player)
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
        
# plot_one_exp from a df_p
def plot_one_exp(df_p, plot_keys, ax, **kwargs):
    ax = df_p[plot_keys].plot(ax=ax, ylim=[-0.1,1.1], **kwargs)
    ax.legend(fontsize=14)
    ax.set_title(kwargs['title'], fontsize = 18)
#     np.arange(-1.21, -0.79, 0.04)
    ax.set_yticks(np.arange(-0.1, 1.1, 0.1))
    ax.grid(True, linestyle='--', alpha=0.3)

# plot_joint_exp from a json filepath
def plot_joint_exp(df_dict, plot_keys, ax, **kwargs):
    plot_keys_p = {
        "Black" : list(filter(lambda x:x.endswith("_Black"), plot_keys)),
        "White" : list(filter(lambda x:x.endswith("_White"), plot_keys)),
        "Joint" : list(filter(lambda x:x.endswith("_Joint"), plot_keys)),
        "JointCount" : list(filter(lambda x:x.endswith("_JointCount"), plot_keys)),
    }
    # separate plots for black and white
    for player in ['Black', 'White', 'Joint', 'JointCount']:
        plot_k = [x.split("_")[0] for x in plot_keys_p[player]]
        if player in ['Black', 'White']:
            for key in plot_k:
                if key == "moveWinrateRange":
                    ax.fill_between(list(df_dict[player].index), 
                    df_dict[player]["minChildWinrate"], df_dict[player]["maxChildWinrate"], alpha=0.2)
                elif key == "moveAttackValueRange":
                    ax.fill_between(list(df_dict[player].index), 
                    df_dict[player]["minChildAttackValue"], df_dict[player]["maxChildAttackValue"], alpha=0.2)
                else:
                    if key == "winrate" and player == "White":
                        ax = (1.0 - df_dict[player][key]).plot(ax=ax, ylim=[-0.1,1.1], label=f'1.0 - {key}_white')
                    else:
                        ax = df_dict[player][key].plot(ax=ax, label=f'{key}_{player}')
        elif player == 'Joint':
            for key in plot_k:
                joint_series = df_dict['Black'][key].copy()
                joint_series.append(df_dict['White'][key])
                ax = joint_series.plot(ax=ax, label=f'{key}_{player}')
        elif player == 'JointCount':
            if len(plot_keys_p['JointCount']) > 0:
                winCount = df_dict["Black"]['winCountMotivGT(white)'] + df_dict["Black"]['winCountPass(white)'] 
                lossCount = df_dict["Black"]['lossCountMotivGT(white)'] + df_dict["Black"]['lossCountPass(white)'] 
                # print(df_dict['Black'].columns)
                ax.fill_between(list(df_dict['Black'].index), 
                        len(lossCount) * [0], lossCount, alpha=0.2)
                ax = lossCount.plot(ax=ax, label=f'lossCount(white)_{player}')
                ax.fill_between(list(df_dict['Black'].index), 
                        lossCount, lossCount + winCount, alpha=0.2)
                ax = (lossCount + winCount).plot(ax=ax, label=f'winCount(white)_{player}')
        else:
            raise
    
    ax.legend(fontsize=14)
    ax.set_title(kwargs['title'], fontsize = 18)
    if 'yticks' in kwargs.keys():
        ax.set_yticks(kwargs['yticks'])
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
        df_dict = dict()
        # loading raw dataframe for both player
        for idx, player in enumerate(["Black", "White"]):
            pklName = f"game-{gameIdx}-{player}.pkl"
            savePath = str(Path(data_dir) / pklName)
            # if pklName in json_list:
            if False:
                pass
            else:
                json_p = str(Path(data_dir) / f"game-{gameIdx}-{player}.json")
                all_p, keys_p = get_preprocessed_all_p(json_p)
                df_dict[player] = dict2df(all_p, keys_p, record_key_dict[player], player)
                if 'scoreStdev/25' in plot_key_dict[player]:
                    df_dict[player]['scoreStdev/25'] = df_dict[player]['scoreStdev'] / 25 
                df_dict[player].to_pickle(savePath)
                print(f"{pklName} saved!")

    # subplots arguments
    twoD = True if numFinishedGames > 1 else False
    assert len(record_key_dict) == len(plot_key_dict)
    ncols = len(record_key_dict)
    # nrows = numFinishedGames (numFinishedGames // 25) * 25
    nrows = min(numFinishedGames, 25)

    # for each game
    gameCount = 0
    fig_all, ax_all = plt.subplots(ncols=ncols, nrows=nrows, figsize=(ncols*8*1.5, nrows*6*1.5))
    fig_game, ax_game = plt.subplots(ncols=ncols, nrows=1, figsize=(ncols*8*1.5, 1*6*1.5))
    for gameIdx in range(numFinishedGames):
        # load df_dict first
        df_dict = dict()
        for idx, player in enumerate(["Black", "White"]):
            pklName = f"game-{gameIdx}-{player}.pkl"
            savePath = str(Path(data_dir) / pklName)
            with open(savePath, "rb") as file:
                df_p = pickle.load(file)
                df_dict[player] = df_p
                print(f"{pklName} loaded!")

        # initialize game figures and start plotting
        gameOutcome = game_result_dict[gameIdx][0]
        attackMoveNums = None

        for idx, player in enumerate(list(plot_key_dict.keys())): 
            ax_all_sub = ax_all[gameIdx % 25, idx] if twoD else ax_all[idx]
            ax_game_sub = ax_game[idx]
            
            plot_keys_p = plot_key_dict[player]
            if player in ["Black", "White"]:
                plot_one_exp(df_dict[player], plot_keys_p, ax_all_sub, title=f"game-{gameIdx}-{player}.json ({gameOutcome})")
                plot_one_exp(df_dict[player], plot_keys_p, ax_game_sub, title=f"game-{gameIdx}-{player}.json ({gameOutcome})")
            elif player in ["JointWin", "JointAttack"]:
                yticks = np.arange(-0.1, 1.1, 0.1)
                plot_joint_exp(df_dict, plot_keys_p, ax_all_sub, title=f"game-{gameIdx}-{player}.json ({gameOutcome})", yticks=yticks)
                plot_joint_exp(df_dict, plot_keys_p, ax_game_sub, title=f"game-{gameIdx}-{player}.json ({gameOutcome})", yticks=yticks)
            elif player in ["JointCount"]:
                plot_joint_exp(df_dict, plot_keys_p, ax_all_sub, title=f"game-{gameIdx}-{player}.json ({gameOutcome})")
                plot_joint_exp(df_dict, plot_keys_p, ax_game_sub, title=f"game-{gameIdx}-{player}.json ({gameOutcome})")
            elif player in ["JointRatio"]:
                winCount = df_dict["Black"]['winCountMotivGT(white)'] + df_dict["Black"]['winCountPass(white)'] 
                lossCount = df_dict["Black"]['lossCountMotivGT(white)'] + df_dict["Black"]['lossCountPass(white)'] 
                if 'win/allCountGT(white)_Black' in plot_keys_p:
                    df_dict["Black"]['win/allCountGT(white)'] = winCount / (winCount + lossCount)
                    # print(df_dict["Black"]['win/allCountGT(white)'])
                if 'loss/allCountGT(white)_Black' in plot_keys_p:
                    df_dict["Black"]['loss/allCountGT(white)'] = lossCount / (winCount + lossCount)
                    # print(df_dict["Black"]['loss/allCountGT(white)'])
                
                yticks = np.arange(-0.1, 1.1, 0.1)
                plot_joint_exp(df_dict, plot_keys_p, ax_all_sub, title=f"game-{gameIdx}-{player}.json ({gameOutcome})", yticks=yticks)
                plot_joint_exp(df_dict, plot_keys_p, ax_game_sub, title=f"game-{gameIdx}-{player}.json ({gameOutcome})", yticks=yticks)
            elif player in ["numChildren"]:
                plot_joint_exp(df_dict, plot_keys_p, ax_all_sub, title=f"game-{gameIdx}-{player}.json ({gameOutcome})")
                plot_joint_exp(df_dict, plot_keys_p, ax_game_sub, title=f"game-{gameIdx}-{player}.json ({gameOutcome})")

            
            # plot attack positions
            if "attack?" in plot_keys_p:
                if player == "Black":
                    attackMoveNums = df_dict[player].index[df_dict[player]["attack?"]]
                for xc in attackMoveNums:
                    ax_all_sub.axvline(x=xc, c="red", alpha=0.4)
                    ax_game_sub.axvline(x=xc, c="red", alpha=0.4)
        
        # plot each game
        gamePlotName = f"game-{gameIdx}"
        fig_game.savefig(str(Path(plot_dir) / gamePlotName) + '.png', format='png')
        fig_game.clear()
        print(f"{gamePlotName} plot finished ... ")

        # add one to gameCount
        gameCount += 1

        # plot 25 games
        if gameCount == 25 or gameIdx + 1 == numFinishedGames:
            allPlotName = f"all_plots{gameIdx-gameCount+1}-{gameIdx}"
            fig_all.savefig(str(Path(plot_dir) / allPlotName) + '.png', format='png')
            fig_all.clear()
            print(f"{allPlotName} plot finished ... ")
            gameCount = 0
            # plt.show()
    
    plt.close()

def plot_recursive(exp_dir, record_key_dict, plot_key_dict):
    filelist = [joinpath(exp_dir, x) for x in os.listdir(exp_dir)]
    subdir_list = list(filter(lambda x: os.path.isdir(x), filelist))
    # print(f"filelist: {filelist}")
    # print(f"subdir_list: {subdir_list}")
    if joinpath(exp_dir, "game.dat") in filelist:
        main(exp_dir, record_key_dict, plot_key_dict)
        return 
    if len(subdir_list) == 0:
        return
    # recurse
    for sd in subdir_list:
        # try:
        plot_recursive(sd, record_key_dict, plot_key_dict)
        # except Exception as e:
        #     print(f"Error {e} occurred during plotting!")

if __name__ == "__main__":

    # set record_keys
    record_keys = ['move', 'visits']
    record_keys += ['attackValue', 'effectiveWinValue', 'minimaxValue']
    record_keys += ['winrate', 'winValueAvg(black)', 'winValueAvg(white)']
    record_keys += ['numChildren', 'perspective']
    record_keys += ['scoreLead', 'scoreStdev', 'utility', 'weightSum']
    record_keys += ['moveAttackValue', 'attack?']
    record_keys += ['moveWinrate', 'maxChildWinrate', 'minChildWinrate', 'childWinrateStd']
    record_keys += ['maxChildAttackValue', 'minChildAttackValue', 'childAttackValueStd']
    record_keys += ['nnWinValue', 'nnWinValue(white)']
    record_keys += ['movePrior']
    record_key_dict = {
        "Black" : copy.copy(record_keys),
        "White" : copy.copy(record_keys),
        "JointWin" : copy.copy(record_keys),
        "JointAttack" : copy.copy(record_keys),
        "JointCount" : copy.copy(record_keys),
        "JointRatio" : copy.copy(record_keys),
        # "numChildren" : copy.copy(record_keys),
    }

    # set plot_keys
    plot_key_dict = {
        "Black" : ['winrate', 'attackValue', 'moveAttackValue', 'minimaxValue', "attack?"],# 'scoreStdev/25'],
        "White" : ['winrate', 'effectiveWinValue', 'minimaxValue', "attack?"],# 'scoreStdev/25'],
        "JointWin" : ['winrate_Black', 'winrate_White', 'moveWinrate_Black', 'moveWinrateRange_Black', 'childWinrateStd_Black', "attack?"],# 'scoreStdev/25'],
        "JointAttack" : ['attackValue_Black', 'winrate_White', 'moveAttackValue_Black', 'moveAttackValueRange_Black', 'childAttackValueStd_Black', "attack?"],# 'scoreStdev/25'],
        "JointCount" : ['winCountRange(white)_JointCount', 'lossCountRange(white)_JointCount'], #, 'winValueAvgMotivGT(black)_Black'],
        "JointRatio" : ['winValueAvgMotivGT(white)_Black'] #, 'winValueAvgMotivGT(black)_Black'],

        # "numChildren" : ['numChildren_Black', 'numChildren_White', 'attack?']
    }
    record_key_dict["Black"] += ['attackUtility', 'effectiveUtility', 'minimaxUtility']
    record_key_dict["Black"] += ['winCountMotivGT(white)', 'winCountPass(white)', 'lossCountMotivGT(white)', 'lossCountPass(white)', 'winValueAvgMotivGT(black)', 'winValueAvgMotivGT(white)']

    plot_key_dict["Black"] += ['winValueAvgMotivGT(black)']
    plot_key_dict["Black"] += ['nnWinValue']
    plot_key_dict["White"] += ['nnWinValue']
    plot_key_dict["JointWin"] += ['nnWinValue(white)_Joint']
    plot_key_dict["JointAttack"] += ['nnWinValue(white)_Joint']
    plot_key_dict["JointRatio"] += ['win/allCountGT(white)_Black', 'loss/allCountGT(white)_Black']

    root = str(Path("..").resolve())
    games_dir = str(Path(root) / "games")
    folder_strs = [
        # "atkexpand",
        # "baseline",
        # "mctssb_atkexpand",
        # "minimaxsb_atkexpand",
        # "softatk",
        # "softatk_atkexpand",
        # "softatk_softexpand",
        # "test-plot"
        # "baseline",
        # "motiv",
        # "test",
        # "full-motiv-gt",
        # "motiv",
        # "motiv-gt",
        # "baseline",
        "motiv-gt-vo"
    ]

    exp_dirs = [joinpath(games_dir, fs) for fs in folder_strs]
    for idx, exp_dir in enumerate(exp_dirs):
        print(f"--------------- Plotting ({idx}, {exp_dir}) ---------------")
        # try:
        plot_recursive(exp_dir, record_key_dict, plot_key_dict)
        # except Exception as e:
        #     print(f"Error {e} occurred during plotting!")
        
            