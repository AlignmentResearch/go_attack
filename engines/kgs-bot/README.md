To run a bot on KGS, from root directory of the repo build the cpp-kgs container, then start it:

`docker build . -f engines/kgs-bot/Dockerfile -t humancompatibleai/goattack:cpp-kgs`

`docker run --gpus all -it humancompatibleai/goattack:cpp-kgs name=USERNAME password=PASSWORD`

USERNAME and PASSWORD should be replaced with the KGS login information for the account the bot will use.

To adjust settings (you will need to rebuild the Dockerfile after editing these files, or bind them in with the `-v` flag to run):
* KGS game and matchmaking: go_attack/engines/kgs-bot/config.txt
* Bot itself: go_attack/configs/kgs-bot/adversary_bot.cfg
* Adversary/victim weight files: go_attack/engines/kgs-bot/Dockerfile and adjust the wgets at the end to the files you want. Or, obtain the weights manually and adjust go_attack/engines/kgs-bot/config.txt to point to them.

The default settings will run the cyclic-adversary trained for 545 million steps.

Please note there may be some configuration differences from the version used in reported experimental results, which could have unknown effects. We have confirmed playing games with Japanese or Chinese rules on KGS will result in very abnormal play. We advise only playing games on KGS with New Zealand rules. 
