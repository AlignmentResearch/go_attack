import os
from os.path import join as joinpath 
from pathlib import Path

def main(args):
    ROOT = (Path(__file__) / ".." / "..").resolve()
    CONFIG_DIR = str(Path(ROOT) / "configs" / "katago")

    # make each codebase first
    os.system(f"cd {ROOT}/engines/KataGo-raw/cpp && make && pwd")
    # os.system("cd $ROOT/engines/KataGo-raw/cpp && make && pwd")

    os.system(f"{ROOT}/engines/KataGo-raw/cpp/katago selfplay -output-dir {ROOT}/selfplay -models-dir {ROOT}/models -config {ROOT}/configs/training/selfplay-custom.cfg ")

if __name__ == "__main__":
    # /goattack/scripts/attack.py -p black --komi 7 --size 9 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 100 -wp 100 \
    # -sa 0 -sb 0 -se 25 -ae -n 10 -e test/test-soft-expand --gpu 0 1 2 3 -f
    import argparse
    parser = argparse.ArgumentParser()
    
    # Game Params
    # parser.add_argument('-n', '--num_games', type=int, default=2)
    # parser.add_argument('-e', '--exp_name', type=str, default="test/test_scripts")
    # parser.add_argument('-t', '--threads', type=int, default=1)
    # parser.add_argument('--size', type=int, default=19)
    # parser.add_argument('--komi', type=float, default=7.5)
    # # parser.add_argument('--gpu', type=str, default="0")
    # parser.add_argument('--gpu', type=int, nargs='+')
    # parser.add_argument('-f', '--force', action='store_true')
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