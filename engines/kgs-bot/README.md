To run a bot on KGS, first build and start cpp-kgs container:

`docker build . -f compose/cpp-kgs/Dockerfile -t humancompatibleai/goattack:cpp-kgs`

`docker run --gpus all -it humancompatibleai/goattack:cpp-kgs name=USERNAME password=PASSWORD`

USERNAME and PASSWORD should be replaced with the KGS login information for the account the bot will use.

To adjust settings (you will need to rebuild the Dockerfile after editing these files, or bind them in with the `-v` flag to run):
* KGS game and matchmaking: go_attack/engines/kgs-bot/config.txt
* Bot itself: go_attack/configs/kgs-bot/adversary_bot.cfg
* Adversary/victim weight files: go_attack/engines/kgs-bot/Dockerfile and adjust the wgets at the end to the files you want. Or, obtain the weights manually and adjust go_attack/engines/kgs-bot/config.txt to point to them.
