import os
from os.path import join as joinpath
from pathlib import Path
from subprocess import Popen
from time import sleep
import signal

def main(args):

    ROOT = (Path(__file__) / ".." / "..").resolve()
    MODEL_DIR = str(Path(ROOT) / "models")
    CONFIG_DIR = str(Path(ROOT) / "configs" / "training")

    models2download = [
            "https://media.katagotraining.org/uploaded/networks/zips/kata1/kata1-b6c96-s175395328-d26788732.zip",
            # "https://media.katagotraining.org/uploaded/networks/zips/kata1/kata1-b6c96-s165180416-d25130434.zip",
            # "https://media.katagotraining.org/uploaded/networks/zips/kata1/kata1-b10c128-s41138688-d27396855.zip",
        ]

    os.system("rm -rf /goattack/selfplay-test")
    os.makedirs("/goattack/selfplay-test/models")
    os.makedirs("/goattack/selfplay-test/selfplay")

    for model_path in models2download:
        model_name = model_path.split('/')[-1]
        if not os.path.exists(joinpath(MODEL_DIR, model_name)):
            os.system(f"cd {MODEL_DIR}; wget {model_path}")
        # os.system(f"rm {joinpath(MODEL_DIR, model_name)}")
        os.system(f"cd {MODEL_DIR}; unzip {model_name} -d /goattack/selfplay-test/models")
    
    sp_list = []
    for gpu in args.gpu:
        script = f"CUDA_VISIBLE_DEVICES={gpu} /goattack/engines/KataGo-custom/cpp/katago selfplay -max-games-total 128 -output-dir /goattack/selfplay-test/selfplay -models-dir /goattack/selfplay-test/models -config /goattack/configs/training/selfplay1.cfg"

        # os.system(script)
        p = Popen(script, shell=True)
        sp_list.append(p)

    while True:
        try:
            sleep(60)
            for p in sp_list:
                if p.poll(): 
                    p.terminate()
                    
        except KeyboardInterrupt:
            print("Sending signals to kill all processes!")
            for p in sp_list:
                p.send_signal(signal.SIGINT)
            break

if __name__ == "__main__":
    # python3 /goattack/scripts/selfplay_test.py -g 1
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-g', '--gpu', nargs='+', type=int, required=True)
    args = parser.parse_args()
    main(args)
