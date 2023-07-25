#!/bin/bash -eu
# shellcheck disable=SC2215,SC2086,SC2089,SC2090,SC2016,SC2034,SC2068

####################
# Argument parsing #
####################

DEFAULT_CURRICULUM="/go_attack/configs/curriculum.json"
DEFAULT_ALTERNATE_CURRICULUM="/go_attack/configs/iterated-training/alternate-curriculum.json"
DEFAULT_LR_SCALE=1.0
DEFAULT_NUM_VICTIMPLAY_GPUS=4

usage() {
  echo "Usage: $0 [--victimplay-gpus GPUS] [--victimplay-max-gpus MAX_GPUS]"
  echo "          [--iterated-training] [--alternate-iteration-first]"
  echo "          [--curriculum CURRICULUM]"
  echo "          [--alternate-curriculum ALTERNATE_CURRICULUM] [--gating]"
  echo "          [--lr-scale LR_SCALE] [--predictor]"
  echo "          [--predictor-warmstart-ckpt CHECKPOINT] [--resume TIMESTAMP]"
  echo "          [--warmstart-ckpt CHECKPOINT] [--victim-ckpt CHECKPOINT]"
  echo "          [--use-weka] PREFIX"
  echo
  echo "positional arguments:"
  echo "  PREFIX  Identifying label used for the name of the job and the name"
  echo "          of the output directory."
  echo
  echo "optional arguments:"
  echo "  -g GPUS, --victimplay-gpus GPUS"
  echo "    Minimum number of GPUs to use for victimplay."
  echo "    default: ${DEFAULT_NUM_VICTIMPLAY_GPUS}"
  echo "  -m GPUS, --victimplay-max-gpus GPUS"
  echo "    Maximum number of GPUs to use for victimplay."
  echo "    default: twice the minimum number of GPUs."
  echo "  --iterated-training"
  echo "    Perform iterated adversarial training."
  echo "  --alternate-iteration-first"
  echo "    Only for iterated training. Use alternate configs on even"
  echo "    (zero-indexed) iterations instead of odd iterations."
  echo "  -c CURRICULUM, --curriculum CURRICULUM"
  echo "    Path to curriculum JSON file to use for victimplay."
  echo "    default: ${DEFAULT_CURRICULUM}"
  echo "  --alternate-curriculum ALTERNATE_CURRICULUM"
  echo "    Path to curriculum JSON file to use on every other iteration in"
  echo "    iterated adversarial training."
  echo "    default: ${DEFAULT_ALTERNATE_CURRICULUM}"
  echo "  --gating"
  echo "    Enable gatekeeping."
  echo "  --lr-scale LR_SCALE"
  echo "    Learning rate scale for training."
  echo "    default: ${DEFAULT_LR_SCALE}"
  echo "  -p, --predictor"
  echo "    Use AMCTS with a predictor network. (A-MCTS-VM)"
  echo "  --predictor-warmstart-ckpt CHECKPOINT"
  echo "    Path to checkpoint's TF weights directory to use for predictor warmstart."
  echo "  -r, --resume TIMESTAMP"
  echo "    Resume a previous run. If this flag is given, the PREFIX argument"
  echo "    must exactly be match the run to be resumed, and the TIMESTAMP"
  echo "    argument should match the timestamp attached to the name of the"
  echo "    previous run's output directory. The use of the --use-weka flag"
  echo "    must also exactly match that of the previous run."
  echo "  --warmstart-ckpt CHECKPOINT"
  echo "    Path to checkpoint's TF weights directory to use for warmstarting"
  echo "    the adversary, e.g.,"
  echo "    /shared/victim-weights/kata1-b40c256-s11840935168-d2898845681 for"
  echo "    cp505, e.g.,"
  echo "    /shared/victimplay/ttseng-avoid-pass-alive-coldstart-39-20221025-175949/models/t0-s545065216-d136760487"
  echo "    for the cyclic-adversary. The corresponding model file is expected"
  echo "    to be in either the TF weights directory or /shared/victims/."
  echo "  --victim-ckpt CHECKPOINT"
  echo "    Only for and is required for iterated training. Path to the TF"
  echo "    weights directory for the last victim (i.e., the bot not"
  echo "    being trained) in the initial iteration's curriculum (CURRICULUM,"
  echo "    or ALTERNATE_CURRICULUM if --alternate-iteration-first is set)."
  echo "  -w, --use-weka"
  echo "    Store results on the go-attack Weka volume instead of the CHAI NAS"
  echo "    volume."
  echo
  echo "Optional arguments should be specified before positional arguments."
  echo
  echo "In iterated adversarial training, after the curriculum CURRICULUM"
  echo "finishes, the run restarts with the latest adversary and"
  echo "victim networks swapped. The curriculum is switched to"
  echo "ALTERNATE_CURRICULUM, the victimplay config is switched from"
  echo "active-experiment.cfg to iterated-training/alternate-experiment.cfg,"
  echo "and the evaluate-loop config is switched from match-1gpu.cfg to"
  echo "iterated-training/alternate-match-1gpu.cfg. This repeats indefinitely"
  echo "with the curriculum and config switching each iteration. The \"name\""
  echo "fields in the curricula are ignored except in the first iteration."
}

ALTERNATE_ITERATION_FIRST=0
CURRICULUM=${DEFAULT_CURRICULUM}
ALTERNATE_CURRICULUM=${DEFAULT_ALTERNATE_CURRICULUM}
LR_SCALE=${DEFAULT_LR_SCALE}
MIN_VICTIMPLAY_GPUS=${DEFAULT_NUM_VICTIMPLAY_GPUS}
USE_GATING=0
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while [ -n "${1-}" ]; do
  case $1 in
    -h|--help) usage; exit 0 ;;
    -g|--victimplay-gpus) MIN_VICTIMPLAY_GPUS=$2; shift ;;
    -m|--victimplay-max-gpus) MAX_VICTIMPLAY_GPUS=$2; shift ;;
    --iterated-training) USE_ITERATED_TRAINING=1 ;;
    --alternate-iteration-first) ALTERNATE_ITERATION_FIRST=1; ;;
    -c|--curriculum) CURRICULUM=$2; shift ;;
    --alternate-curriculum) ALTERNATE_CURRICULUM=$2; shift ;;
    --gating) USE_GATING=1 ;;
    --lr-scale) LR_SCALE=$2; shift ;;
    -p|--predictor) USE_PREDICTOR=1 ;;
    --predictor-warmstart-ckpt) PREDICTOR_WARMSTART_CKPT=$2; shift ;;
    -r|--resume) RESUME_TIMESTAMP=$2; shift ;;
    --warmstart-ckpt) WARMSTART_CKPT=$2; shift ;;
    --victim-ckpt) VICTIM_CKPT=$2; shift ;;
    -w|--use-weka) export USE_WEKA=1 ;;
    --selfplay-proportion) SELFPLAY_PROPORTION=$2; shift ;;
    -*) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
    *) break ;;
  esac
  shift
done
NUM_POSITIONAL_ARGUMENTS=1
if [ $# -ne ${NUM_POSITIONAL_ARGUMENTS} ]; then
  usage
  exit 1
fi

MAX_VICTIMPLAY_GPUS=${MAX_VICTIMPLAY_GPUS:-$((2*MIN_VICTIMPLAY_GPUS))}

############################
# Launching the experiment #
############################

RUN_NAME="$1-${RESUME_TIMESTAMP:-$(date +%Y%m%d-%H%M%S)}"
echo "Run name: $RUN_NAME"

VOLUME_NAME="shared"
source "$(dirname "$(readlink -f "$0")")"/launch-common.sh
update_images "cpp python"

if [ -n "${USE_PREDICTOR:-}" ]; then
  if [ -n "${USE_ITERATED_TRAINING:-}" ]; then
    echo "Using predictor networks with iterated training is not yet"\
         "implemented."
    exit 1
  fi

  PREDICTOR_FLAG="-p $RUN_NAME/predictor"
  VICTIMPLAY_CMD="/go_attack/kubernetes/victimplay-predictor.sh"

  # shellcheck disable=SC2215,SC2086,SC2089,SC2090
  ctl job run --container \
      "$PYTHON_IMAGE" \
      "$PYTHON_IMAGE" \
      $VOLUME_FLAGS \
      --command "/go_attack/kubernetes/shuffle-and-export.sh $RUN_NAME $RUN_NAME/predictor $VOLUME_NAME" \
      "/go_attack/kubernetes/train.sh --initial-weights $PREDICTOR_WARMSTART_CKPT $RUN_NAME/predictor $VOLUME_NAME $LR_SCALE" \
      --high-priority \
      --gpu 0 1 \
      --name go-training-"$1"-predictor
else
  PREDICTOR_FLAG=""
  VICTIMPLAY_CMD="/go_attack/kubernetes/victimplay.sh"
fi

if [ -n "${WARMSTART_CKPT:-}" ]; then
  VICTIMPLAY_FLAGS="--warmstart"
  TRAIN_FLAGS="--copy-initial-model --initial-weights $WARMSTART_CKPT"
else
  VICTIMPLAY_FLAGS=""
  TRAIN_FLAGS=""
fi

if [ -n "${USE_ITERATED_TRAINING:-}" ]; then
  if [ -z "${VICTIM_CKPT:-}" ]; then
    echo "--victim-ckpt must be specified for iterated training."
    exit 1
  fi
  VICTIMPLAY_CMD="/go_attack/kubernetes/iterated-training/victimplay.sh $VICTIMPLAY_FLAGS $RUN_NAME $VOLUME_NAME $ALTERNATE_ITERATION_FIRST"
  EVALUATE_LOOP_CMD="/go_attack/kubernetes/iterated-training/evaluate_loop.sh $RUN_NAME $VOLUME_NAME $ALTERNATE_ITERATION_FIRST"
  TRAIN_CMD="/go_attack/kubernetes/iterated-training/train.sh $TRAIN_FLAGS $RUN_NAME $VOLUME_NAME $LR_SCALE $VICTIM_CKPT"
  SHUFFLE_AND_EXPORT_CMD="/go_attack/kubernetes/iterated-training/shuffle-and-export.sh $RUN_NAME $VOLUME_NAME"
  CURRICULUM_CMD="/go_attack/kubernetes/iterated-training/curriculum.sh $RUN_NAME $VOLUME_NAME $CURRICULUM $ALTERNATE_CURRICULUM $ALTERNATE_ITERATION_FIRST"
else
  VICTIMPLAY_CMD+=" $VICTIMPLAY_FLAGS $RUN_NAME $VOLUME_NAME"
  EVALUATE_LOOP_CMD="/engines/KataGo-custom/cpp/evaluate_loop_custom.sh $PREDICTOR_FLAG /$VOLUME_NAME/train-only/$RUN_NAME /$VOLUME_NAME/train-only/$RUN_NAME/eval"
  TRAIN_CMD="/go_attack/kubernetes/train.sh $TRAIN_FLAGS $RUN_NAME $VOLUME_NAME $LR_SCALE"
  SHUFFLE_AND_EXPORT_CMD="/go_attack/kubernetes/shuffle-and-export.sh $RUN_NAME $RUN_NAME $VOLUME_NAME $USE_GATING $SELFPLAY_PROPORTION"
  CURRICULUM_CMD="/go_attack/kubernetes/curriculum.sh $RUN_NAME $VOLUME_NAME $CURRICULUM"
fi

# shellcheck disable=SC2215,SC2086,SC2089,SC2090
ctl job run --container \
    "$CPP_IMAGE" \
    "$PYTHON_IMAGE" \
    "$PYTHON_IMAGE" \
    $VOLUME_FLAGS \
    --command \
    "$EVALUATE_LOOP_CMD" \
    "$TRAIN_CMD" \
    "$SHUFFLE_AND_EXPORT_CMD" \
    --high-priority \
    --gpu 1 1 0 \
    --memory 16Gi 64Gi 64Gi \
    --name gtonly-"$1" \
    --replicas 1 1 1

exit 0

if [ "$USE_GATING" -eq 1 ]; then
  if [ -n "${USE_ITERATED_TRAINING:-}" ]; then
    echo "Using gating with iterated training is not yet implemented."
    exit 1
  fi
  ctl job run --container \
      "$CPP_IMAGE" \
      $VOLUME_FLAGS \
      --command "/go_attack/kubernetes/gatekeeper.sh $RUN_NAME $VOLUME_NAME" \
      --high-priority \
      --gpu 1 \
      --name go-train-"$1"-gate \
      --replicas 1
fi

EXTRA_VICTIMPLAY_GPUS=$((MAX_VICTIMPLAY_GPUS-MIN_VICTIMPLAY_GPUS))
if [ $EXTRA_VICTIMPLAY_GPUS -gt 0 ]; then
  # shellcheck disable=SC2086
  ctl job run --container \
      "$CPP_IMAGE" \
      $VOLUME_FLAGS \
      --command "$VICTIMPLAY_CMD" \
      --gpu 1 \
      --name go-train-"$1"-extra \
      --replicas "${EXTRA_VICTIMPLAY_GPUS}"
fi
