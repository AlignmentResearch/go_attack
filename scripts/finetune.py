import os
from os.path import join as joinpath 
from pathlib import Path
from subprocess import Popen

import signal
import subprocess
from time import sleep

# /goattack/engines/KataGo-custom/cpp/katago selfplay -output-dir /goattack/selfplay-base/selfplay -models-dir /goattack/selfplay-base/models -max-games-total 1000 -config /goattack/configs/training/selfplay-custom.cfg 
# cd /goattack/engines/KataGo-custom/python; ./selfplay/shuffle_and_export_loop.sh attack1 /goattack/selfplay-base/ /goattack/selfplay-base/scratch 1 128 0
# cd /goattack/engines/KataGo-custom/python; ./selfplay/train.sh /goattack/selfplay-base/ test b6c96 128 main -lr-scale 1.0

def main(args):
    ROOT = (Path(__file__) / ".." / "..").resolve()
    BASEDIR = str(Path(ROOT) / "selfplay-exps" / "baseline")
    CONFIG_DIR = str(Path(ROOT) / "configs" / "training")
    katago_used = "KataGo-custom"

    if args.force:
        os.system(f"rm -rf {BASEDIR}/*")

    # make each codebase first
    os.system(f"cd {ROOT}/engines/{katago_used}/cpp && make && pwd")
    
    # subprocess list
    script_dict = {}
    sp_list = []

    # Selfplay engine (C++ - cpp/katago selfplay)
    MAX_GAME_TOTAL = args.max_game_selfplay
    script_dict['selfplay'] = f"CUDA_VISIBLE_DEVICES=0,1 {ROOT}/engines/{katago_used}/cpp/katago selfplay " + \
                    f"-output-dir {BASEDIR}/selfplay " + \
                    f"-models-dir {BASEDIR}/models " + \
                    f"-max-games-total {MAX_GAME_TOTAL} " + \
                    f"-config {CONFIG_DIR}/selfplay-custom.cfg "
    
    # Shuffler (python - python/shuffle.py & python/export.py)
    NAMEOFRUN =  args.name_of_run
    NUM_THREADS = args.num_threads
    BATCH_SIZE = args.batch_size
    MIN_ROWS = args.min_rows
    USE_GATING = args.use_gating

    script_dict['shuffle_export'] = f"cd {ROOT}/engines/{katago_used}/python; " + \
                                    f"./selfplay/shuffle_and_export_loop.sh " + \
                                    f"{NAMEOFRUN} {BASEDIR} {BASEDIR}/scratch {NUM_THREADS} {BATCH_SIZE} " + \
                                    f"{MIN_ROWS} {int(USE_GATING)}"

    # Training (python - python/train.py) 
    TRAININGNAME = args.training_name
    script_dict['train'] =  f"cd {ROOT}/engines/{katago_used}/python; CUDA_VISIBLE_DEVICES=2 ./selfplay/train.sh " + \
                            f"{BASEDIR} {TRAININGNAME} b6c96 {BATCH_SIZE} main -lr-scale 1.0"

    # Gatekeeper (C++ - cpp/katago gatekeeper) 
    if USE_GATING:
        script_dict['gatekeeper'] = f"CUDA_VISIBLE_DEVICES=3 {ROOT}/engines/{katago_used}/cpp/katago gatekeeper " + \
            f"-rejected-models-dir {BASEDIR}/rejectedmodels " + \
            f"-accepted-models-dir {BASEDIR}/models/ " + \
            f"-sgf-output-dir {BASEDIR}/gatekeepersgf/ " + \
            f"-test-models-dir {BASEDIR}/modelstobetested/ " + \
            f"-selfplay-dir {BASEDIR}/selfplay/ " + \
            f"-config {CONFIG_DIR}/gatekeeper-custom.cfg "

    # Running scripts
    for key in ['selfplay', 'shuffle_export', 'train', 'gatekeeper']:
        if key not in script_dict.keys():
            continue
        script = script_dict[key]
        p = Popen(script, shell=True)
        sp_list.append(p)
        print(f"Running {script}")


    while True:
        try:
            sleep(60)
        except KeyboardInterrupt:
            print("Sending signals to kill all processes!")
            for p in sp_list:
                p.send_signal(signal.SIGINT)
            break
    

if __name__ == "__main__":
    # CUDA_VISIBLE_DEVICES=0,1 python3 scripts/finetune.py --min_rows 25000 --use_gating -f
    import argparse
    parser = argparse.ArgumentParser()
    
    # Game Params
    parser.add_argument('-f', '--force', action='store_true')
    parser.add_argument('--max_game_selfplay', type=int, default=1000000000)

    parser.add_argument('--min_rows', type=int, default=250000)
    parser.add_argument('--num_threads', type=int, default=1)
    parser.add_argument('--batch_size', type=int, default=128)
    parser.add_argument('--use_gating', action='store_true')

    parser.add_argument('--name_of_run', type=str, default="test1")
    parser.add_argument('--training_name', type=str, default="baseline")

    # parser.add_argument('-n', '--num_games', type=int, default=2)
    # parser.add_argument('-e', '--exp_name', type=str, default="test/test_scripts")
    # parser.add_argument('-t', '--threads', type=int, default=1)
    # parser.add_argument('--size', type=int, default=19)
    # parser.add_argument('--komi', type=float, default=7.5)
    # # parser.add_argument('--gpu', type=str, default="0")
    # parser.add_argument('--gpu', type=int, nargs='+')
    # parser.add_argument('-a', '--alternate', action='store_true')
    # parser.add_argument('-o', '--opening', action='store_true')

    # # Player Params
    # parser.add_argument('-bp', '--black_playouts', type=int, default=1600)
    # parser.add_argument('-wp', '--white_playouts', type=int, default=1600)
    # parser.add_argument('-b', '--black', type=str, default="gtp_black.cfg")
    # parser.add_argument('-w', '--white', type=str, default="gtp_white.cfg")
    # parser.add_argument('-p', '--attack_player', type=str, default=None)

    # # Attack Params
    # parser.add_argument('-ae', '--attack_expand', action='store_true')
    # parser.add_argument('-gt', '--motiv_gt', action='store_true')
    # parser.add_argument('-gt_vo', '--motiv_gt_vo', action='store_true')
    # parser.add_argument('-sa', '--soft_attack', type=int, default=65536)
    # parser.add_argument('-sb', '--soft_backup', type=int, default=0)
    # parser.add_argument('-se', '--soft_expand', type=int, default=0)
    # parser.add_argument('-ms', '--minimax_softbackup', action='store_true')

    args = parser.parse_args()

    main(args)