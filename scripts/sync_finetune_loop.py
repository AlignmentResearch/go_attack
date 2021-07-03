import re
import os
from os.path import join as joinpath 
import shutil

def main(args):
    basedir = args.base_dir
    if args.force:
        os.system(f"rm -rf {basedir}")
    os.makedirs(basedir, exist_ok=True)

    # loading initial weights to the scratch agent
    traindir = joinpath(basedir, "train", args.training_name)
    os.makedirs(traindir, exist_ok=True)

    init_weight_dir = joinpath(traindir, "initial_weights")
    if not os.path.exists(init_weight_dir) and args.initial_weights:
        shutil.copytree(args.initial_weights, init_weight_dir)
        for var_name in os.listdir(init_weight_dir):
            model_name = re.sub("variables", "model", var_name)
            os.rename(joinpath(init_weight_dir, var_name), joinpath(init_weight_dir, model_name))

    os.system(f"cd /goattack/engines/KataGo-custom/python; CUDA_VISIBLE_DEVICES={args.gpu} /goattack/engines/KataGo-custom/python/selfplay/synchronous_loop_fast.sh " +
              f"{args.name_prefix} {basedir} {args.training_name} {args.model} {int(args.use_gating)}")


if __name__ == "__main__":
    # python3 sync_loop.py --gpu 1 --initial_weights /goattack/models/b6c96-s175395328-d26788732 --name_prefix finetune --base_dir /goattack/selfplay-exps/finetune --training_name fine1 --use_gating
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument("--gpu", type=int, required=True, help="Indicating which GPU to use")
    parser.add_argument("-m", "--model", type=str, default='b6c96', help="Indicating the model structure to use")
    parser.add_argument("--initial_weights", type=str, help="Path to the initial weights file")
    parser.add_argument("--use_gating", action="store_true", help="Indicating whether to use gating")
    parser.add_argument("--name_prefix", type=str, help="string prefix for this training run, try to pick something globally unique. Will be displayed to users when KataGo loads the model.")
    parser.add_argument("--base_dir", type=str, help="containing selfplay data and models and related directories.")
    parser.add_argument("--training_name", type=str, help="name to prefix models with, specific to this training daemon")

    parser.add_argument("-f", "--force", action="store_true", help="Force reinit the training run")
    args = parser.parse_args()
    print(args)
    main(args)
