# How to run our adversary using Sabaki

## Sabaki setup
Sabaki is a cross-platform application for playing Go and editing SGF files.
You can install Sabaki from https://sabaki.yichuanshen.de/.
If you are on MacOS, you can install using Homebrew with the command
`brew install sabaki`.

## Download adversary and victim neural nets
Run `sabaki/scripts/download-models.sh`
to automatically download the strongest adversaries and KataGo models.

We host the models on Google Drive here: https://drive.google.com/drive/folders/1-bGX-NQOh6MuRPoXJgYHb9-jWRJvviSg?usp=sharing

The base KataGo models are downloaded from https://katagotraining.org/networks/.

## Bot setup
0. First build the C++ KataGo executable.
   To do this, 
   you'll want to run the following commands in both the
   `engines/KataGo-custom/cpp`
   and
   `engines/KataGo-raw/cpp`
   directories.
   ```
   cmake . -DUSE_BACKEND=OPENCL -DUSE_TCMALLOC=1
   make -j
   ```
   Adjust the backend and whether to use tcmalloc as needed. See https://github.com/lightvector/KataGo/blob/master/Compiling.md for detailed compilation instructions.
1. Open up Sabaki preferences. On macOS, press command comma (⌘,), on Linux go to "File->Preferences", and on other platforms go to Preferences in the top-level drop-down menu. 
2. Go to the Engines tab. Then click the "Add" button on the bottom left to add a new config for our adversary.
3. A sample config would be the following:
  ![bot-config-screenshot](bot-config-screenshot.png)
  The first line is a name for our engine (this can be anything),
  the second line is the path to the executable,
  the third line is the flags passed to the executable,
  and the fourth line is the initial commands passed to gtp
  (in this case giving the bot infinite time to make moves).
4. After adding a config, you can follow the instructions at https://youtu.be/6ZA_saVHyTA to play against newly configured engine.

## More sample bot configs
```
# Strongest cyclic-adversary
cyclic-adv-s545m-v600-vm-cp505-v1-s
/Users/ttw/code/go_attack/engines/KataGo-custom/cpp/katago
gtp -model /Users/ttw/code/go_attack/sabaki/models/adv/cyclic-adv-s545065216-d136760487.bin.gz -victim-model /Users/ttw/code/go_attack/sabaki/models/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz -config /Users/ttw/code/go_attack/configs/gtp/gtp-adv600-vm1-s.cfg
time_settings 0 1 0

# Weaker cyclic-adversary (with dragonslayer strategy)
cyclic-adv-s349m-v600-vm-cp505-v1-s
/Users/ttw/code/go_attack/engines/KataGo-custom/cpp/katago
gtp -model /Users/ttw/code/go_attack/sabaki/models/adv/cyclic-adv-s349284096-d87808728.bin.gz -victim-model /Users/ttw/code/go_attack/sabaki/models/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz -config /Users/ttw/code/go_attack/configs/gtp/gtp-adv600-vm1-s.cfg
time_settings 0 1 0

# Pass-trick adversary
pass-adv-s34m-v600-vs-cp505-v1-s
/Users/ttw/code/go_attack/engines/KataGo-custom/cpp/katago
gtp -model /Users/ttw/code/go_attack/sabaki/models/adv/pass-adv-s34090496-d8262123.bin.gz -victim-model /Users/ttw/code/go_attack/sabaki/models/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz -config /Users/ttw/code/go_attack/configs/gtp/gtp-adv600-vm1-s.cfg 
time_settings 0 1 0

# Latest with 128 visits
cp505-v128
/Users/ttw/code/go_attack/engines/KataGo-raw/cpp/katago
gtp -model /Users/ttw/code/go_attack/sabaki/models/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz -config /Users/ttw/code/go_attack/configs/gtp/gtp-v128.cfg
time_settings 0 1 0

# Latest with no search
cp505-v1
/Users/ttw/code/go_attack/engines/KataGo-raw/cpp/katago
gtp -model /Users/ttw/code/go_attack/sabaki/models/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz -config /Users/ttw/code/go_attack/configs/gtp/gtp-v1.cfg
time_settings 0 1 0

# Cyclic-adversary over ssh
ssh-adv505h-s545m-v600-vm-cp505-v1-s
ssh
rnn -tt 'bash -l -c "/nas/ucb/tony/go-attack/gtp-host/go_attack/sabaki/scripts/docker-katago-custom.sh gtp -model /models/adv/cyclic-adv-s545065216-d136760487.bin.gz -victim-model /models/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz -config /go_attack/configs/gtp/gtp-adv600-vm1-s.cfg"'
time_settings 0 1 0
```
