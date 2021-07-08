import os
from os.path import join as joinpath 
from pathlib import Path
from subprocess import Popen
import signal
from time import sleep


def main(args):
    BASEDIR = args.base_dir

    # subprocess list
    script_dict = {}
    sp_list = []

    # compile each codebase first
    os.makedirs(f"/home/{args.user}{BASEDIR}/models", exist_ok=True)
    os.makedirs(f"/home/{args.user}{BASEDIR}/selfplay", exist_ok=True)
    os.makedirs(f"/home/{args.user}{BASEDIR}/tmp_download", exist_ok=True)

    while True:
        try:
            print("\n----------------------------------------")
            print(f"Try to download model from {args.user}@{args.server}:/home/{args.user}{BASEDIR}/activemodel/*")

            # Download models for selfplay
            down_script = f"scp -r {args.user}@{args.server}:/home/{args.user}{BASEDIR}/activemodel/* " + \
                                        f"/home/{args.user}{BASEDIR}/tmp_download"
            os.system(down_script)
            download_model_list = os.listdir(f"/home/{args.user}{BASEDIR}/tmp_download")
            download_model_name = download_model_list[0] if len(download_model_list) > 0 else None
            if download_model_name and not os.path.exists(f"/home/{args.user}{BASEDIR}/models/{download_model_name}"):
                os.rename(f"/home/{args.user}{BASEDIR}/tmp_download/{download_model_name}", 
                    f"/home/{args.user}{BASEDIR}/models/{download_model_name}")
                print("New model downloaded")
            else:
                os.system(f"rf -rf /home/{args.user}{BASEDIR}/tmp_download/{download_model_name}")
            
            # Uploading selfplay data for shuffling and training 
            selfplaydir = joinpath(f"/home/{args.user}{BASEDIR}", "selfplay")
            selfplay_data_mtime_list = [(name, os.path.getmtime(joinpath(selfplaydir, name))) for name in os.listdir(selfplaydir) if not 'log' in name]
            selfplay_log_mtime_list = [(name, os.path.getmtime(joinpath(selfplaydir, name))) for name in os.listdir(selfplaydir) if 'log' in name]
            selfplay_data_mtime_list.sort(key=lambda x: x[-1], reverse=True)
            selfplay_log_mtime_list.sort(key=lambda x: x[-1], reverse=True)
            
            print(selfplay_data_mtime_list)
            print(selfplay_log_mtime_list)
            for names in selfplay_log_mtime_list:
                name = names[0]
                os.system(f"scp /home/{args.user}{BASEDIR}/selfplay/{name} " + \
                                f"{args.user}@{args.server}:/home/{args.user}{BASEDIR}/selfplay")

            for names in selfplay_data_mtime_list[:5]:
                name = names[0]
                os.system(f"scp -r /home/{args.user}{BASEDIR}/selfplay/{name} " + \
                                f"{args.user}@{args.server}:/home/{args.user}{BASEDIR}/selfplay")
            # for selfplay_mtime_list
            # if not os.path.exists(joinpath(BASEDIR, "activemodel", latest_model_name)):
            #     os.system(f"rm -rf {joinpath(BASEDIR, 'activemodel/*')}")
            #     shutil.copytree(joinpath(modeldir, latest_model_name), joinpath(BASEDIR, "activemodel", latest_model_name))
            #     print(f"Copying {latest_model_name} to activemodel ...")
            # up_script = f"scp -r {args.user}@{args.server}:/home/{args.user}{BASEDIR}/activemodel/* " + \
            #                             f"/home/{args.user}{BASEDIR}/models"

            sleep(60)
        except KeyboardInterrupt:
            print("Done!")
            break
    

if __name__ == "__main__":
    # python3 scripts/download_upload_worker.py --base_dir /goattack/selfplay-exps/dist-test
    # python3 scripts/download_upload_worker.py --base_dir /goattack/selfplay-exps/dist-test --gpus 0 -m /goattack/models/kata1-b6c96-s165180416-d25130434.zip
    import argparse
    parser = argparse.ArgumentParser()
    
    # Download Params
    parser.add_argument('--user', type=str, default="yawen")
    parser.add_argument('--server', type=str, default="perceptron.bair.berkeley.edu")

    # Selfplay Params
    parser.add_argument('--base_dir', type=str, required=True)
    parser.add_argument('-f', '--force', action='store_true')
    args = parser.parse_args()

    main(args)