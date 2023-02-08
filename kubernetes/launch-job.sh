#!/bin/bash -eu
# shellcheck disable=SC2215,SC2086,SC2089,SC2090,SC2016,SC2034,SC2068

####################
# Argument parsing #
####################

DEFAULT_CURRICULUM="/go_attack/configs/curriculum.json"
DEFAULT_LR_SCALE=1.0
DEFAULT_NUM_VICTIMPLAY_GPUS=4

usage() {
  echo "Usage: $0 [--victimplay-gpus GPUS] [--victimplay-max-gpus MAX_GPUS]"
  echo "          [--curriculum CURRICULUM] [--gating] [--lr-scale]"
  echo "          [--predictor] [--predictor-warmstart-ckpt CHECKPOINT]"
  echo "          [--resume TIMESTAMP] [--warmstart-ckpt CHECKPOINT]"
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
  echo "  -c CURRICULUM, --curriculum CURRICULUM"
  echo "    Path to curriculum json file to use for victimplay."
  echo "    default: ${DEFAULT_CURRICULUM}"
  echo "  --gating"
  echo "    Enable gatekeeping."
  echo "  --lr-scale"
  echo "    Learning rate scale for training."
  echo "    default: ${DEFAULT_LR_SCALE}"
  echo "  -p, --predictor"
  echo "    Use AMCTS with a predictor network. (A-MCTS-VM)"
  echo "  --predictor-warmstart-ckpt CHECKPOINT"
  echo "    Name of checkpoint's TF weights directory to use for predictor warmstart."
  echo "  -r, --resume TIMESTAMP"
  echo "    Resume a previous run. If this flag is given, the PREFIX argument"
  echo "    must exactly be match the run to be resumed, and the TIMESTAMP"
  echo "    argument should match the timestamp attached to the name of the"
  echo "    previous run's output directory. The use of the --use-weka flag"
  echo "    must also exactly match that of the previous run."
  echo "  --warmstart-ckpt CHECKPOINT"
  echo "    Name to checkpoint's TF weights directory to use for warmstarting"
  echo "    the adversary, e.g., b6c96-s175395328-d26788732 for cp63 or"
  echo "    kata1-b40c256-s11840935168-d2898845681 for cp505."
  echo "  -w, --use-weka"
  echo "    Store results on the go-attack Weka volume instead of the CHAI NAS"
  echo "    volume."
  echo
  echo "Optional arguments should be specified before positional arguments."
}

CURRICULUM=${DEFAULT_CURRICULUM}
LR_SCALE=${DEFAULT_LR_SCALE}
MIN_VICTIMPLAY_GPUS=${DEFAULT_NUM_VICTIMPLAY_GPUS}
USE_GATING=0
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while [ -n "${1-}" ]; do
  case $1 in
    -h|--help) usage; exit 0 ;;
    -g|--victimplay-gpus) MIN_VICTIMPLAY_GPUS=$2; shift ;;
    -m|--victimplay-max-gpus) MAX_VICTIMPLAY_GPUS=$2; shift ;;
    -c|--curriculum) CURRICULUM=$2; shift ;;
    --gating) USE_GATING=1 ;;
    --lr-scale) LR_SCALE=$2; shift ;;
    -p|--predictor) USE_PREDICTOR=1 ;;
    --predictor-warmstart-ckpt) PREDICTOR_WARMSTART_CKPT=$2; shift ;;
    -r|--resume) RESUME_TIMESTAMP=$2; shift ;;
    --warmstart-ckpt) WARMSTART_CKPT=$2; shift ;;
    -w|--use-weka) export USE_WEKA=1 ;;
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
  USE_WARMSTART=1
  TRAIN_FLAGS="--copy-initial-model --initial-weights $WARMSTART_CKPT"
else
  USE_WARMSTART=0
  TRAIN_FLAGS=""
fi

# shellcheck disable=SC2215,SC2086,SC2089,SC2090
ctl job run --container \
    "$CPP_IMAGE" \
    "$CPP_IMAGE" \
    "$PYTHON_IMAGE" \
    "$PYTHON_IMAGE" \
    $VOLUME_FLAGS \
    --command "$VICTIMPLAY_CMD $RUN_NAME $VOLUME_NAME $USE_WARMSTART" \
    "/engines/KataGo-custom/cpp/evaluate_loop.sh $PREDICTOR_FLAG /$VOLUME_NAME/victimplay/$RUN_NAME /$VOLUME_NAME/victimplay/$RUN_NAME/eval" \
    "/go_attack/kubernetes/train.sh $TRAIN_FLAGS $RUN_NAME $VOLUME_NAME $LR_SCALE" \
    "/go_attack/kubernetes/shuffle-and-export.sh $RUN_NAME $RUN_NAME $VOLUME_NAME $USE_GATING" \
    --high-priority \
    --gpu 1 1 1 0 \
    --name go-train-"$1"-vital \
    --replicas "${MIN_VICTIMPLAY_GPUS}" 1 1 1

if [ "$USE_GATING" -eq 1 ]; then
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
      --command "$VICTIMPLAY_CMD $RUN_NAME $VOLUME_NAME $USE_WARMSTART" \
      --gpu 1 \
      --name go-train-"$1"-extra \
      --replicas "${EXTRA_VICTIMPLAY_GPUS}"
fi
