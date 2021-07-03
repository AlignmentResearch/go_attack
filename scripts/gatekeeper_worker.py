import os
from os.path import join as joinpath 
from pathlib import Path
from subprocess import Popen

import signal
import subprocess
from time import sleep

def main(args):
    ROOT = (Path(__file__) / ".." / "..").resolve()
    BASEDIR = args.base_dir
    # MODEL_DIR = str(Path(ROOT) / "models")
    CONFIG_DIR = str(Path(ROOT) / "configs" / "training")
    katago_used = "KataGo-custom"

    if args.force:
        for d in ["gatekeepersgf", "rejectedmodels"]:
            os.system(f"rm -rf {joinpath(BASEDIR, d)}")

    # Gatekeeper (C++ - cpp/katago gatekeeper) 
    script = f"CUDA_VISIBLE_DEVICES={args.gpu} {ROOT}/engines/{katago_used}/cpp/katago gatekeeper " + \
        f"-rejected-models-dir {BASEDIR}/rejectedmodels " + \
        f"-accepted-models-dir {BASEDIR}/models/ " + \
        f"-sgf-output-dir {BASEDIR}/gatekeepersgf/ " + \
        f"-test-models-dir {BASEDIR}/modelstobetested/ " + \
        f"-selfplay-dir {BASEDIR}/selfplay/ " + \
        f"-config {CONFIG_DIR}/gatekeeper1.cfg "

    # Running scripts
    p = Popen(script, shell=True)
    print(f"Running {script}")

    while True:
        try:
            sleep(60)
        except KeyboardInterrupt:
            print("Sending signals to kill all processes!")
            p.send_signal(signal.SIGINT)
            break
    

if __name__ == "__main__":
    # python3 scripts/gatekeeper_worker.py --base_dir /goattack/selfplay-exps/dist-test -g 0
    import argparse
    parser = argparse.ArgumentParser()
    
    # Gatekeeper Params
    parser.add_argument('--base_dir', type=str, required=True)
    parser.add_argument('-g', '--gpu', type=str, required=True)
    parser.add_argument('-f', '--force', action='store_true')

    args = parser.parse_args()

    main(args)