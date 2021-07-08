import os
from os.path import join as joinpath 
from pathlib import Path
from subprocess import Popen
import signal
from time import sleep

def main(args):
    ROOT = (Path(__file__) / ".." / "..").resolve()
    BASEDIR = args.base_dir
    # MODEL_DIR = str(Path(ROOT) / "models")
    CONFIG_DIR = str(Path(ROOT) / "configs" / "training")
    MAX_GAME_TOTAL = args.max_game_selfplay
    katago_used = "KataGo-custom"

    if args.force:
        for d in ["models", "selfplay"]:
            os.system(f"rm -rf {joinpath(BASEDIR, d)}")

    # compile each codebase first
    os.system(f"cd {ROOT}/engines/{katago_used}/cpp && make && pwd")

    os.makedirs(f"{BASEDIR}/models", exist_ok=True)
    os.makedirs(f"{BASEDIR}/selfplay", exist_ok=True)

    if args.load_initial_model:
        assert args.load_initial_model.endswith('.zip')
        initial_model_name = (args.load_initial_model.split('/')[-1]).split('.')[0]
        if os.path.exists(args.load_initial_model) and not os.path.exists(f"{BASEDIR}/models/{initial_model_name}"):
            os.system(f"unzip {args.load_initial_model} -d {BASEDIR}/models")

    # Selfplay engine (C++ - cpp/katago selfplay)
    if args.mode == 'master':
        os.system(f"chmod 777 -R {BASEDIR}/models")
        os.system(f"chmod 777 -R {BASEDIR}/selfplay")
    script = f"CUDA_VISIBLE_DEVICES={','.join(args.gpus)} {ROOT}/engines/{katago_used}/cpp/katago selfplay " + \
                    f"-output-dir {BASEDIR}/selfplay " + \
                    f"-models-dir {BASEDIR}/models " + \
                    f"-max-games-total {MAX_GAME_TOTAL} " + \
                    f"-config {CONFIG_DIR}/selfplay-custom{len(args.gpus)}.cfg "

    # Running scripts
    p = Popen(script, shell=True)
    print(f"Running {script}")

    while True:
        try:
            if args.mode == 'master':
                os.system(f"chmod 777 -R {BASEDIR}/models")
                os.system(f"chmod 777 -R {BASEDIR}/selfplay")
            sleep(60)
        except KeyboardInterrupt:
            print("Sending signals to kill all processes!")
            p.send_signal(signal.SIGINT)
            break
    

if __name__ == "__main__":
    # python3 scripts/selfplay_worker.py --base_dir /goattack/selfplay-exps/dist-test --gpus 0 -m /goattack/models/kata1-b6c96-s165180416-d25130434.zip
    import argparse
    parser = argparse.ArgumentParser()
    
    # Selfplay Params
    parser.add_argument('--base_dir', type=str, required=True)
    parser.add_argument('-m', '--load_initial_model', type=str, default=None)
    parser.add_argument('-g', '--gpus', nargs='+', type=str, required=True)
    parser.add_argument('--max_game_selfplay', type=int, default=10000)
    parser.add_argument('--mode', type=str, default='worker')
    parser.add_argument('-f', '--force', action='store_true')
    args = parser.parse_args()

    main(args)