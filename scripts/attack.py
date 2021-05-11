import os
from os.path import join as joinpath 
from pathlib import Path

def main(args):
    ROOT = (Path(__file__) / ".." / "..").resolve()
    EXP_DIR = str(Path(ROOT) / "games" / args.exp_name)
    CONFIG_DIR = str(Path(ROOT) / "configs" / "katago")

    config_dict = {
        "black" : joinpath(EXP_DIR, args.__dict__["black"]),
        "white" : joinpath(EXP_DIR, args.__dict__["white"])
    }

    print(f"ROOT: {ROOT}")
    print(f"EXP_DIR: {EXP_DIR}")
    print(f"CONFIG_DIR: {CONFIG_DIR}")
    print(f"config_dict: {config_dict}")
    print(args)

    # if using -f flag, deleting the whole exp directory
    if args.force:
        os.system(f"rm -rf {EXP_DIR}")

    # Building experiment directory
    game_file=f"{EXP_DIR}/game"
    os.makedirs(EXP_DIR, exist_ok=True)

    # Setting BLACK and WHITE configs
    katago = joinpath(ROOT, "engines/KataGo-custom/cpp/katago")
    BLACK = f"{katago} gtp -model {ROOT}/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz "
    BLACK += f"-config {EXP_DIR}/black.cfg"
    WHITE = f"{katago} gtp -model {ROOT}/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz "
    WHITE += f"-config {EXP_DIR}/white.cfg"

    # get start game index
    start_game_idx = len(list(filter(lambda x: x.endswith(".sgf"), os.listdir(EXP_DIR))))
    
    for player in ["black", "white"]:
        # Removing previous configs
        if os.path.exists(config_dict[player]):
            os.remove(config_dict[player])
        
        # Write new configs
        with open(joinpath(EXP_DIR, f"{player}.cfg"), "w") as file:
            file.write(f"startGameIdx = {start_game_idx}    # Start game index\n")
            if args.attack_player == player:
                file.write(f"visitsThreshold2Attack = {args.soft_attack}    # Soft threshold to apply soft attack\n")
                file.write(f"optimismThreshold4Backup = {args.soft_backup}    # Optimism threshold to apply soft attack\n")
                file.write(f"attackExpand = {str(args.attack_expand).lower()}    # Tree expansion according to attack value\n")
                file.write(f"softExpandThreshold = {args.soft_expand}    # Tree soft expansion according to attack value\n")
                file.write(f"isMinimaxOptim4Backup = {str(args.minimax_softbackup).lower()}    # is minimax soft backup\n")
                file.write(f"attackPla = {player.upper()}    # {player} player as the attack player\n")

            file.write(f"logDir = {EXP_DIR}/gtp_logs    # Each run of KataGo will log to a separate file in this dir\n")
            file.write(f"jsonDir = {EXP_DIR}/data_logs \n")
            file.write(f"maxPlayouts = {args.__dict__[f'{player}_playouts']} \n")
            
            assert args.gpu is not None
            file.write(f"numNNServerThreadsPerModel = {len(args.gpu)}\n")
            for i, g in enumerate(args.gpu):
                file.write(f"cudaDeviceToUseThread{i} = {g}\n")
            
            with open(joinpath(CONFIG_DIR, args.__dict__[player]), "r") as file2:
                file.write(file2.read())
            
    game_args = f"-games {args.num_games} "
    game_args += f"-size {args.size} "
    game_args += f"-komi {args.komi} "
    game_args += f"-sgffile {game_file} "
    game_args += f"-threads {args.threads} "
    game_args += "-auto -verbose "

    if args.alternate:
        game_args += "-alternate "
    
    if args.opening:
        game_args += f"-openings {joinpath(ROOT, 'openings')} "

    # recording the shell command
    with open(joinpath(EXP_DIR, "game.log"), "a+") as log:
        log.write("Key Shell Commands for the game: \n")
        log.write(f"BLACK=\"{BLACK}\"\n")
        log.write(f"WHITE=\"{WHITE}\"\n")
        log.write(f"{ROOT}/controllers/gogui/bin/gogui-twogtp -black $BLACK -white $WHITE {game_args}")

    # make each codebase first
    os.system(f"cd {ROOT}/engines/KataGo-custom/cpp && make && pwd")
    # os.system("cd $ROOT/engines/KataGo-raw/cpp && make && pwd")
    # print(f"bash {ROOT}/controllers/gogui/bin/gogui-twogtp -black \"{BLACK}\" -white \"{WHITE}\" {game_args}")
    os.system(f"bash {ROOT}/controllers/gogui/bin/gogui-twogtp -black \"{BLACK}\" -white \"{WHITE}\" {game_args}")

if __name__ == "__main__":
    # /goattack/scripts/attack.py -p black --komi 7 --size 9 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 100 -wp 100 \
    # -sa 0 -sb 0 -se 25 -ae -n 10 -e test/test-soft-expand --gpu 0 1 2 3 -f
    import argparse
    parser = argparse.ArgumentParser()
    
    # Game Params
    parser.add_argument('-n', '--num_games', type=int, default=2)
    parser.add_argument('-e', '--exp_name', type=str, default="test/test_scripts")
    parser.add_argument('-t', '--threads', type=int, default=1)
    parser.add_argument('--size', type=int, default=19)
    parser.add_argument('--komi', type=int, default=7.5)
    # parser.add_argument('--gpu', type=str, default="0")
    parser.add_argument('--gpu', type=int, nargs='+')
    parser.add_argument('-f', '--force', action='store_true')
    parser.add_argument('-a', '--alternate', action='store_true')
    parser.add_argument('-o', '--opening', action='store_true')

    # Player Params
    parser.add_argument('-bp', '--black_playouts', type=int, default=1600)
    parser.add_argument('-wp', '--white_playouts', type=int, default=1600)
    parser.add_argument('-b', '--black', type=str, default="gtp_black.cfg")
    parser.add_argument('-w', '--white', type=str, default="gtp_white.cfg")
    parser.add_argument('-p', '--attack_player', type=str, default=None)

    # Attack Params
    parser.add_argument('-ae', '--attack_expand', action='store_true')
    parser.add_argument('-sa', '--soft_attack', type=int, default=0)
    parser.add_argument('-sb', '--soft_backup', type=int, default=-1)
    parser.add_argument('-se', '--soft_expand', type=int, default=0)
    parser.add_argument('-ms', '--minimax_softbackup', action='store_true')

    args = parser.parse_args()

    main(args)