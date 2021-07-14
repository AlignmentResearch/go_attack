import os
from os.path import join as joinpath 
from pathlib import Path
from subprocess import Popen
import signal
from time import sleep
import shutil
import re

def main(args):
    ROOT = (Path(__file__) / ".." / "..").resolve()
    BASEDIR = args.base_dir
    MODEL_DIR = str(Path(ROOT) / "models")
    CONFIG_DIR = str(Path(ROOT) / "configs" / "training")
    katago_used = "KataGo-custom"

    if args.force:
        for d in ["logs", "models_extra", "modelstobetested", "scratch", "scripts", "shuffleddata", "tfsavedmodels_toexport", "tfsavedmodels_toexport_extra", "train", "tmp"]:
            os.system(f"rm -rf {joinpath(BASEDIR, d)}")
    
    # subprocess list
    script_dict = {}
    sp_list = []
    
    # Shuffler & Export (python - python/shuffle.py & python/export.py)
    NAMEOFRUN =  args.name_of_run
    NUM_THREADS = args.num_threads
    BATCH_SIZE = args.batch_size
    MIN_ROWS = args.min_rows
    USE_GATING = args.use_gating

    script_dict['shuffle_export'] = f"cd {ROOT}/engines/{katago_used}/python; " + \
                                    f"CUDA_VISIBLE_DEVICES={args.export_gpu} ./selfplay/shuffle_and_export_loop.sh " + \
                                    f"{NAMEOFRUN} {BASEDIR} {BASEDIR}/scratch {NUM_THREADS} {BATCH_SIZE} " + \
                                    f"{MIN_ROWS} {int(USE_GATING)}"

    # Training (python - python/train.py) 
    
    # make each codebase first
    os.system(f"cd {ROOT}/engines/{katago_used}/cpp && make && pwd")
    traindir = joinpath(BASEDIR, "train", args.training_name)
    
    os.makedirs(traindir, exist_ok=True)
    init_weight_dir = joinpath(traindir, "initial_weights")
    
    if not os.path.exists(init_weight_dir) and args.load_initial_weights:
        assert os.path.exists(args.load_initial_weights)
        assert args.load_initial_weights.endswith('.zip')
        # initial_model_name = (args.load_initial_weights.split('/')[-1]).split('.')[0]
        os.makedirs(f"{BASEDIR}/tmp", exist_ok=True)
        os.system(f"unzip {args.load_initial_weights} -d {BASEDIR}/tmp")

        initial_model_name = os.listdir(f"{BASEDIR}/tmp")[0]
        shutil.copytree(f"{BASEDIR}/tmp/{initial_model_name}/saved_model/variables", init_weight_dir)
        shutil.copy(f"{BASEDIR}/tmp/{initial_model_name}/saved_model/model.config.json", traindir)
        for var_name in os.listdir(init_weight_dir):
            model_name = re.sub("variables", "model", var_name)
            os.rename(joinpath(init_weight_dir, var_name), joinpath(init_weight_dir, model_name))
        os.system(f"rm -rf {BASEDIR}/tmp")

    TRAININGNAME = args.training_name
    LR_SCALE = args.lr_scale
    script_dict['train'] =  f"cd {ROOT}/engines/{katago_used}/python; CUDA_VISIBLE_DEVICES={args.gpu} ./selfplay/train.sh " + \
                            f"{BASEDIR} {TRAININGNAME} b6c96 {BATCH_SIZE} main -lr-scale {str(LR_SCALE)} "
    if args.max_epoch:
        MAX_EPOCHS_THIS_INSTANCE = args.max_epoch
        script_dict['train'] += f"-max-epochs-this-instance {MAX_EPOCHS_THIS_INSTANCE}"
                            # f"{BASEDIR} {TRAININGNAME} b40c256 {BATCH_SIZE} main -lr-scale {str(LR_SCALE)} -max-epochs-this-instance {MAX_EPOCHS_THIS_INSTANCE}"
    
    # Running scripts
    for key in ['shuffle_export', 'train']:
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
    # python3 scripts/shuffle_train_export_worker.py --base_dir /goattack/selfplay-exps/dist-test --min_rows 250000 --name_of_run dist --use_gating --training_name dist1 --load_initial_weights /goattack/models/kata1-b6c96-s165180416-d25130434.zip --lr-scale 0.1 -g 0 --export_gpu 2
    import argparse
    parser = argparse.ArgumentParser()
    
    # Shuffle & Exporting Params
    parser.add_argument('--base_dir', type=str, required=True)
    parser.add_argument('--name_of_run', type=str, default="test1", required=True)
    parser.add_argument('--num_threads', type=int, default=8)
    parser.add_argument('--batch_size', type=int, default=128)
    parser.add_argument('--min_rows', type=int, default=250000)
    parser.add_argument('--use_gating', action='store_true')

    # Training Params
    parser.add_argument('-g', '--gpu', type=str, required=True)
    parser.add_argument('--export_gpu', type=str, required=True)
    parser.add_argument("--load_initial_weights", type=str, default=None, help="Path to the initial weights file")
    parser.add_argument('--training_name', type=str, default="baseline", required=True)
    parser.add_argument('--lr-scale', type=float, default=1.0)
    parser.add_argument('--max_epoch', type=int, default=None)

    parser.add_argument('-f', '--force', action='store_true')
    
    args = parser.parse_args()

    main(args)