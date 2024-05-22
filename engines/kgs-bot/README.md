To run a bot on KGS, from root directory of the repo build the cpp-kgs container, then start it:

`docker build . -f engines/kgs-bot/Dockerfile -t ANONYMOUS_USERNAME/goattack:cpp-kgs`

`docker run --gpus all -it ANONYMOUS_USERNAME/goattack:cpp-kgs name=USERNAME password=PASSWORD`

USERNAME and PASSWORD should be replaced with the KGS login information for the account the bot will use.

To adjust settings (you will need to rebuild the Dockerfile after editing these files, or bind them in with the `-v` flag to run):
* KGS game and matchmaking: ANONYMOUS_REPO/engines/kgs-bot/config.txt
* Bot itself: ANONYMOUS_REPO/configs/kgs-bot/adversary_bot.cfg
* Adversary/victim weight files: ANONYMOUS_REPO/engines/kgs-bot/Dockerfile and adjust the wgets at the end to the files you want. Or, obtain the weights manually and adjust ANONYMOUS_REPO/engines/kgs-bot/config.txt to point to them.

The default settings will run the cyclic-adversary trained for 545 million steps.

Please note there may be some configuration differences from the version used in reported experimental results, which could have unknown effects. We have confirmed playing games with Japanese or Chinese rules on KGS will result in very abnormal play. We advise only playing games on KGS with New Zealand rules. 
