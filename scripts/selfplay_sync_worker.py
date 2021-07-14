import os
from os.path import join as joinpath 
from pathlib import Path
from subprocess import Popen
import signal
from time import sleep


def main(args):
    BASEDIR = args.base_dir
    models_dir = f"/home/{args.user}{BASEDIR}/models"
    selfplay_dir = f"/home/{args.user}{BASEDIR}/selfplay"

    # make necessary directories for selfplay
    os.makedirs(BASEDIR, exist_ok=True)
    os.makedirs(joinpath(BASEDIR, "models"), exist_ok=True)
    os.makedirs(joinpath(BASEDIR, "selfplay"), exist_ok=True)

    # subprocess list
    script_dict = {}
    sp_list = []

    script_dict['models'] = f"sshfs {args.user}@{args.server}:{models_dir} {joinpath(BASEDIR, 'models')} -o IdentityFile=/base/id_rsa,auto_cache,reconnect"
    script_dict['selfplay'] = f"sshfs {args.user}@{args.server}:{selfplay_dir} {joinpath(BASEDIR, 'selfplay')} -o IdentityFile=/base/id_rsa,auto_cache,reconnect"

    print("\n----------------------------------------")
    print(f"Mounting {args.user}@{args.server}:{models_dir} to {BASEDIR}/models")
    print(f"Mounting {args.user}@{args.server}:{selfplay_dir} to {BASEDIR}/selfplay")

    # Running scripts
    for key in ['models', 'selfplay']:
        script = script_dict[key]
        p = Popen(script, shell=True)
        sp_list.append(p)
        print(f"Running {script}")

    while True:
        try:
            sleep(60)
        except KeyboardInterrupt:
            os.system(f"umount {BASEDIR}/models")
            os.system(f"umount {BASEDIR}/selfplay")
            print(f"Unmounted {models_dir}")
            print(f"Unmounted {selfplay_dir}")
            print("----------------------------------------\n")
            for p in sp_list:
                p.send_signal(signal.SIGINT)
            break


if __name__ == "__main__":
    # python3 scripts/selfplay_sync_worker.py --base_dir /goattack/selfplay-exps/dist-test
    import argparse
    parser = argparse.ArgumentParser()
    
    # Download Params
    parser.add_argument('--user', type=str, default="yawen")
    parser.add_argument('--server', type=str, default="perceptron.bair.berkeley.edu")

    # Selfplay Params
    parser.add_argument('--base_dir', type=str, required=True)
    args = parser.parse_args()

    main(args)