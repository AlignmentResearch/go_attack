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

    if args.motiv_gt:
        assert (int(args.opening) + int(args.motiv_gt)) in [0, 2], "Motivation function must be accompanied by motivation board!"
        assert not args.motiv_gt_vo, "Can only select ground truth visible only or ground truth"
    
    if args.motiv_gt_vo:
        assert (int(args.opening) + int(args.motiv_gt_vo)) in [0, 2], "Motivation function must be accompanied by motivation board!"
        assert not args.motiv_gt, "Can only select ground truth visible only or ground truth"

    # if using -f flag, deleting the whole exp directory
    if args.force:
        os.system(f"rm -rf {EXP_DIR}")

    # Building experiment directory
    game_file=f"{EXP_DIR}/game"
    os.makedirs(EXP_DIR, exist_ok=True)

    # Setting BLACK and WHITE configs
    katago = joinpath(ROOT, "engines/KataGo-custom/cpp/katago")
    # BLACK = f"{katago} gtp -model {ROOT}/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz "
    BLACK = f"{katago} gtp -model {ROOT}/models/kata1-b6c96-s175395328-d26788732.txt.gz "
    BLACK += f"-config {EXP_DIR}/black.cfg"
    
    # WHITE = f"{katago} gtp -model {ROOT}/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz "
    WHITE = f"{katago} gtp -model {ROOT}/models/kata1-b6c96-s175395328-d26788732.txt.gz "
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
                file.write(f"motivGroundTruth = {str(args.motiv_gt or args.motiv_gt_vo).lower()}    # Providing ground truth value function for motivation board\n")
                file.write(f"motivGroundTruthVisibleOnly = {str(args.motiv_gt_vo).lower()}    # Providing ground truth value function visible only for motivation board\n")
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
        # game_args += f"-openings {joinpath(ROOT, 'openings', f'motiv{args.size}')} "
        game_args += f"-openings {joinpath(ROOT, 'openings')} "

    # recording the shell command
    with open(joinpath(EXP_DIR, "game.log"), "a+") as log:
        log.write("Key Shell Commands for the game: \n")
        log.write(f"BLACK=\"{BLACK}\"\n")
        log.write(f"WHITE=\"{WHITE}\"\n")
        log.write(f"{ROOT}/controllers/gogui/bin/gogui-twogtp -black $BLACK -white $WHITE {game_args}")

    # compile each codebase first
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
    parser.add_argument('-n', '--num_games', type=int, default=2, help='Specify the number of games to play in this experiment')
    parser.add_argument('-e', '--exp_name', type=str, default="test/test_scripts", help='Specify directory name of current experiment, postfix to /goattack/games/')
    parser.add_argument('-t', '--threads', type=int, default=1, help='Specify the number of threads to play games simultaneously')
    parser.add_argument('--size', type=int, default=19, help='Specify board size')
    parser.add_argument('--komi', type=float, default=7.5, help='Specify komi')
    parser.add_argument('--gpu', type=int, nargs='+', help='Specify GPU indices to use')
    parser.add_argument('-f', '--force', action='store_true', help='Delete the whole experiment directory if specified')
    parser.add_argument('-a', '--alternate', action='store_true', help='Alternate white/black player after each game if specified')
    parser.add_argument('-o', '--opening', action='store_true', help='Starting the game from board state contained in /goattack/openings (e.g. Motivation board) if specified')

    # Player Params
    parser.add_argument('-bp', '--black_playouts', type=int, default=1600, help='Specify number of playouts for black')
    parser.add_argument('-wp', '--white_playouts', type=int, default=1600, help='Specify number of playouts for white')
    parser.add_argument('-b', '--black', type=str, default="gtp_black.cfg", help='Specify the basic config file from /goattack/configs/katago for black, this file will be copied to the experiment directory and be modified. The agent loads the modified config file instead of this one.')
    parser.add_argument('-w', '--white', type=str, default="gtp_white.cfg", help='Specify the basic config file from /goattack/configs/katago for white, this file will be copied to the experiment directory and be modified. The agent loads the modified config file instead of this one.')
    parser.add_argument('-p', '--attack_player', type=str, default=None, help='Specify the player to attack, can select from \"white\", \"black\". Both will be regular agent if not specified.')

    # Attack Params -- parameters below can only be activated only if '--attack_player' is specified
    parser.add_argument('-gt', '--motiv_gt', action='store_true', help='Provide the attack agent with Ground Truth Value, if specified.')
    parser.add_argument('-gt_vo', '--motiv_gt_vo', action='store_true', help='Provide the attack agent with visibility of Ground Truth Value, but not taking actions using this, if specified.')
    parser.add_argument('-sa', '--soft_attack', type=int, default=65536, help='Consider a child as an attack candidate if number of its node visits > this threshold. The attack will happen when this child’s attackValue > the regular move’s attackValue.')
    parser.add_argument('-ae', '--attack_expand', action='store_true', help='During tree expansion, expand its children according to its attack value, if specified.')
    parser.add_argument('-se', '--soft_expand', type=int, default=0, help='Apply attack expansion on nodes with number of visits higher than this threshold, while apply regular expansion on less visited nodes, if specified. This only works if --attack_expand is specified.')
    parser.add_argument('-sb', '--soft_backup', type=int, default=0, help='During backup, replace the attackValue of a child as MCTS value if the child\'s nodeVisits < this threshold.')
    parser.add_argument('-ms', '--minimax_softbackup', action='store_true', help='Use minimaxValue as replacement in soft backup instead of MCTS value.')

    args = parser.parse_args()

    main(args)