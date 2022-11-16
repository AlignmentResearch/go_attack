To run a bot on KGS, first build and start cpp-kgs container:

`docker build . -f compose/cpp-kgs/Dockerfile -t humancompatibleai/goattack:cpp-kgs`

`docker run --gpus all -v ~/go_attack:/go_attack -it humancompatibleai/goattack:cpp-kgs`

Then activate the connection to KGS:

`cd go_attack/engines/kgs-bot/`

`java -jar kgsGtp.jar config.txt name=USERNAME password=PASSWORD`
  
USERNAME and PASSWORD should be replaced with the KGS login information for the account the bot will use.

To adjust settings:
* KGS game and matchmaking: go_attack/engines/kgs-bot/config.txt
* Bot itself: go_attack/configs/kgs-bot/adversary_bot.cfg
* Adversary/victim weight files: go_attack/compose/cpp-kgs/Dockerfile and adjust the wgets at the end to the files you want. Or, obtain the weights manually and adjust go_attack/engines/kgs-bot/config.txt to point to them.
