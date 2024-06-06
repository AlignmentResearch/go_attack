Here we give examples of how to launch training runs similar to those in our
papers. The examples should give you a sense of how to launch your own training
runs or fine-tune our models.

For warmstarting, you will need to download our [models and training
data](https://drive.google.com/drive/u/3/folders/1-bGX-NQOh6MuRPoXJgYHb9-jWRJvviSg)
hosted on Google Drive. You may find [gdown](https://github.com/wkentaro/gdown)
useful for downloading files from Google Drive.

The victims listed in the curriculum files need to be available at
`/shared/victims` and are mostly [publicly available KataGo
networks](https://katagotraining.org/networks/).

## Cyclic adversary

Use the commands in [this repo's root README](../../README.md) without any
warmstarting to launch a training run similar to the original cyclic adversary.

## Pass adversary

Besides using the `configs/examples/pass-adversary-curriculum.json` curriculum
config, the curriculum should omit the `-harden-below-visits` flag for the
curriculum. All the other adversary training runs use `-harden-below-visits` to
avoid degenerating into a pass attack.

## `attack-may23`

`attack-may23` is the fine-tuned adversary from "Adversarial Policies Beat
Superhuman Go AIs".

Here we need to warmstart from the original cyclic adversary:
* From Google Drive, download the `cyclic-adversary-s545m` model directory
  and the `training-data/cyclic-adversary.tar.gz` training data.
* Untar the training data.
* Pass the flag `--initial-weights <path to models>/cyclic-adversary-s545m` to
  the train script.
* Pass the flag `--preseed <path to training
  data>/cyclic-adversary` to the shuffle-and-export
  script. (In our original `attack-may23` run we did not use data pre-seeding,
  but in later training runs we found that pre-seeding made training more
  stable.)
* Pass the flag `--warmstart` to the victim-play script.

Use the `configs/examples/attack-may23-curriculum.json` curriculum config.

This is the general recipe for fine-tuning: warmstart from the starting
adversary using the aforementioned flags and change the curriculum to point at a
different victim.

## `continuous-adversary`

The continuous adversary needs to be warmstarted from `attack-may23`:
* Download the `attack-may23` model, the `training-data/attack-may23.tar.gz`
  training data, _and_ the `training-data/cyclic-adversary.tar.gz` training
  data.
* Untar both training data tarballs.
* Since `attack-may23` itself was warmstarted from `cyclic-adversary`, symlink
  `cyclic-adversary` into `attack-may23` as `ln -s <path to training
  data>/cyclic-adversary <path to training data>/attack-may23/prev-selfplay`.
* Pass the flag `--initial-weights <path to models>/attack-may23-s168m` to the
  train script.
* Pass the flag `--preseed <path to training data>/attack-may23` to the
  shuffle-and-export script.
* Pass the flag `--warmstart` to the victim-play script.

For the curriculum, we started with a curriculum similar to
`configs/examples/continuous-adversary-curriculum.json` that only lists one
victim model with increasing victim visits. Then we periodically checked the
[KataGo website](https://katagotraining.org/networks/) for new networks and
manually updated the curriculum.

E.g., suppose the curriculum has currently progressed to 512 victim visits
against `kata1-b18c384nbt-s8526915840-d3929217702.bin.gz`, and we see on the
KataGo website that a newer network `kata1-b18c384nbt-s8617907712-d3952620469`
is available. Then we download the new network into `/shared/victims`, replace
all instances of `kata1-b18c384nbt-s8526915840-d3929217702` with
`kata1-b18c384nbt-s8617907712-d3952620469` in the curriculum config, remove all
lower visit counts <512 from the curriculum config, and relaunch the curriculum
with the new config.

## `gift-adversary`:

The gift adversary is warmstarted from an early checkpoint of the original
cyclic adversary:
* From Google Drive, download the `cyclic-adversary-early-s227m` model
  directory and the `training-data/cyclic-adversary.tar.gz` training data.
* Untar the training data.
* Pass the flag `--initial-weights <path to
  models>/cyclic-adversary-early-s227m` to the train script.
* Pass the flag `--preseed <path to training
  data>/cyclic-adversary/t0-s227013120-d57265857` to the shuffle-and-export
  script.
* Pass the flag `--warmstart` to the victim-play script.

Use the `configs/examples/gift-adversary-curriculum.json` curriculum config. You
will also need to pass the flag `--config
/go_attack/configs/gift-adversary-experiment.cfg` before the positional
arguments to the victim-play script. Moreover, when running the resulting
adversary (including with `kubernetes/evaluate-loop.sh`), you will need to set
the KataGo config parameters `forceAllowNoResultPredictions = true` and
`noResultUtility = -1.6` for the adversary.

## Iterated adversarial training

### First defense iteration

The model is warmstarted from the KataGo network
`kata1-b40c256-s11840935168-d2898845681`.
* Download both the network file and the TF weights from the [KataGo
  website](https://katagotraining.org/networks/).
* Move the network file to `/shared/victims`.
* Untar the TF weights.
* Pass the flag `--initial-weights <TF weights path>` to
  the train script. Reduce the learning rate by changing the last positional
  argument from `1.0` to `0.1`.
* Download the network's [training
  data](https://katagoarchive.org/kata1/trainingdata/index.html). Instead of
  downloading all the data, you can download the data from 2022-04-25 to
  2022-06-24 (the model's release data) inclusive. Untar all of the tarballs and
  place them in some directory. Then point the `--preseed` shuffle-and-export
  flag to the directory, and add a flag `-add-to-window 2852985812` after the
  positional arguments to tell the shuffler that 2.85 billion data rows have
  been omitted.  Downloading 2022-04-25 to 2022-06-24 data is enough to populate
  the shuffler's sliding window.
* Pass the flags `--warmstart --config
  /go_attack/configs/iterated-training/alternate-experiment.cfg` to the
  victim-play script.
* Use the curriculum config
  `/go_attack/configs/iterated-training/alternate-curriculum.json`.
* If using `evaluate-loop.sh`, pass it the flag `--config
  /go_attack/configs/iterated-training/alternate-match-1gpu.cfg`.

### First attack iteration

Warmstart from the cyclic adversary (see `attack-may23` instructions). After
symlinking the final model of the first defense iteration into `/shared/victims`
where the curriculum script looks for victim models, use a curriculum config
that points towards the final model from the first defense iteration (e.g., copy
`configs/examples/continuous-adversary-curriculum.json` but replace the victim
model name with the defense iteration's model).

### Subsequent iterations

On subsequent [defense/attack] iterations, update the curriculum to point at the
latest [attack/defense] iteration's model and either warmstart from or resume
the previous [defense/attack] iteration.

(Although `kubernetes/iterated-training` contains experimental scripts for
automating switching between attack and defense iterations, for our published
experiments we switched iterations manually and did not use those scripts.)

## `atari-adversary`

Like the gift-adversary, the atari adversary should be warmstarted from the
early cyclic adversary checkpoint using the same instructions.

Use the `configs/examples/atari-adversary-curriculum.json` curriculum config.
The victim `v9` is available on Google Drive.

## `ViT-victim`

The ViT model is trained with self-play rather than victim-play, so
* do not launch the curriculum.
* launch self-play workers by passing the `--selfplay` flag to the victim-play
  script. (The script still saves the experiment in `/shared/victimplay` because
  other scripts in `kubernetes/` assume experiments are located in
  `/shared/victimplay`.)
* pass a self-play config (e.g., any config in
  `engines/KataGo-custom/cpp/configs/training/selfplay*.cfg`) with the
  `--config` flag to the victim-play script. (In our ViT training run, we
  modified the configs to disable rule variation and rectangular boards, but
  this is not necessary.)

`kubernetes/evaluate-loop.sh` also will not work since it reads from a directory
created by the curriculum, though it is straightforward to modify it to evaluate
trained models against some fixed KataGo network instead of against curriculum
victim models.

The ViT model is trained and exported as a PyTorch model, so
* training needs the extra flag `--use-pytorch` before its positional arguments.
  You will also need to specify the model architecture with the flag
  `--model-kind vitp2b4c384` (`vitp2b4c384` is a 4-block ViT; see
  `engines/KataGo-custom/python/modelconfigs.py` to see available model kinds or
  to define your own.)
* shuffle-and-export needs the extra flags `--use-pytorch --use-torchscript`.
* the bot will need to have KataGo config params `useNHWC = false` and
  `inputsUseNHWC = false`.

If you first train a smaller ViT and then want to use its generated data to
pre-train a larger ViT, then
* launch only shuffle-and-export and the training process. To speed up training, you may
  want to train with multiple GPUs by appending the flag `-multi-gpus <GPU
  indices, e.g., "0,1,2,3">` to the training script.
* slowly copy the smaller ViT's training data into the larger ViT's directory,
  using a script like `vit-link-pretraining.sh`.
* only launch the self-play workers after the pre-training has finished.

If the ViT training is overfitting, try increasing the shuffler sliding window
size by adding the flag `-min-rows <some number, e.g., 10000000>` after the
positional arguments to the shuffle-and-export script.

## `ViT-adversary`

Warmstart from the cyclic adversary (see `attack-may23` instructions). Use the
`vit-adversary-curriculum.json` curriculum config. The victim will need the
KataGo config params `useNHWC = false` and `inputsUseNHWC = false` since it is a
Torchscript model.
