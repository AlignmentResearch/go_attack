# How to set up Sabaki

You can install Sabaki from https://sabaki.yichuanshen.de/.
If you are on MacOS, you can install using Homebrew with the command
`brew install sabaki`.

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
1. Open up Sabaki preferences by pressing command comma (⌘,).
2. Go to the Engines tab.
3. A sample config would be the following:
  ![bot-config-screenshot](bot-config-screenshot.png)
  The first line is the bot name,
  the second line is the path to the executable,
  the third line is the flags passed to the executable,
  and the fourth line is the initial commands passed to gtp
  (in this case giving the bot infinite time to make moves).

## List of bot configs

Adversary models can be downloaded from
https://drive.google.com/drive/folders/1-bGX-NQOh6MuRPoXJgYHb9-jWRJvviSg?usp=sharing.
Base KataGo models can be downloaded from
https://katagotraining.org/networks/.

Run `scripts/download-models.sh`
to automatically download the strongest adversaries and KataGo models.

```
# Stronger Dragonslayer
adv505h-s497721856-v600-vm-cp505-v1-s
/Users/ttw/code/go_attack/engines/KataGo-custom/cpp/katago
gtp -model /Users/ttw/code/go_attack/models/adv/adv505h-s497721856-d125043118.bin.gz -victim-model /Users/ttw/code/go_attack/models/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz -config /Users/ttw/code/go_attack/configs/gtp/gtp-adv600-vm1-s.cfg
time_settings 0 1 0

# Dragonslayer
adv505h-s349284096-v600-vm-cp505-v1-s
/Users/ttw/code/go_attack/engines/KataGo-custom/cpp/katago
gtp -model /Users/ttw/code/go_attack/models/adv/adv505h-s349284096-d87808728.bin.gz -victim-model /Users/ttw/code/go_attack/models/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz -config /Users/ttw/code/go_attack/configs/gtp/gtp-adv600-vm1-s.cfg
time_settings 0 1 0

# Pass-trick adversary
adv505-s34090496-v600-vs-cp505-v1-s
/Users/ttw/code/go_attack/engines/KataGo-custom/cpp/katago
gtp -model /Users/ttw/code/go_attack/models/adv/adv505-34090496.bin.gz -victim-model /Users/ttw/code/go_attack/models/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz -config /Users/ttw/code/go_attack/configs/gtp/gtp-adv600-vm1-s.cfg 
time_settings 0 1 0

# Latest with 128 visits
cp505-v128
/Users/ttw/code/go_attack/engines/KataGo-raw/cpp/katago
gtp -model /Users/ttw/code/go_attack/models/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz -config /Users/ttw/code/go_attack/configs/gtp/gtp-v128.cfg
time_settings 0 1 0

# Latest with no search
cp505-v1
/Users/ttw/code/go_attack/engines/KataGo-raw/cpp/katago
gtp -model /Users/ttw/code/go_attack/models/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz -config /Users/ttw/code/go_attack/configs/gtp/gtp-v1.cfg
time_settings 0 1 0

# Stronger dragonslayer over ssh
ssh-adv505h-s497721856-v600-vm-cp505-v1-s
/Users/ttw/code/go_attack/sabaki/scripts/ssh-katago-custom.sh
gtp -model /models/adv/adv505h-s497721856-d125043118.bin.gz -victim-model /models/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz -config /go_attack/configs/gtp/gtp-adv600-vm1-s.cfg
time_settings 0 1 0

# Dragonslayer over ssh
ssh-adv505h-s349284096-v600-vm-cp505-v1-s
/Users/ttw/code/go_attack/sabaki/scripts/ssh-katago-custom.sh
gtp -model /models/adv/adv505h-s349284096-d87808728.bin.gz -victim-model /models/victims/kata1-b40c256-s11840935168-d2898845681.bin.gz -config /go_attack/configs/gtp/gtp-adv600-vm1-s.cfg
time_settings 0 1 0
```
