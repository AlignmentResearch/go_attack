#!/bin/bash -e
# shellcheck disable=SC2215,SC2086,SC2089,SC2090,SC2016,SC2034,SC2068

####################
# Argument parsing #
####################

DEFAULT_LR_SCALE=1
DEFAULT_NUM_VICTIMPLAY_GPUS=4

usage() {
  echo "Usage: $0 [--victimplay-gpus GPUS] [--victimplay-max-gpus MAX_GPUS]"
  echo "          [--curriculum CURRICULUM] [--predictor] [--predictor-warmstart-ckpt]"
  echo "          [--resume TIMESTAMP] [--use-weka] PREFIX"
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
  echo "  -p, --predictor"
  echo "    Use AMCTS with a predictor network. (A-MCTS-VM)"
  echo "  --lr-scale"
  echo "    Learning rate scale for training.
  echo "    default: ${DEFAULT_LR_SCALE}
  echo "  --predictor-warmstart-ckpt"
  echo "    Path to checkpoint to use for predictor warmstart."
  echo "  -r, --resume TIMESTAMP"
  echo "    Resume a previous run. If this flag is given, the PREFIX argument"
  echo "    must exactly be match the run to be resumed, and the TIMESTAMP"
  echo "    argument should match the timestamp attached to the name of the"
  echo "    previous run's output directory. The use of the --use-weka flag"
  echo "    must also exactly match that of the previous run."
  echo "  -w, --use-weka"
  echo "    Store results on the go-attack Weka volume instead of the CHAI NAS"
  echo "    volume."
  echo
  echo "Optional arguments should be specified before positional arguments."
}

MIN_VICTIMPLAY_GPUS=${DEFAULT_NUM_VICTIMPLAY_GPUS}
LR_SCALE=${DEFAULT_LR_SCALE}
# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while true; do
  case $1 in
    -h|--help) usage; exit 0 ;;
    -g|--victimplay-gpus) MIN_VICTIMPLAY_GPUS=$2; shift ;;
    -m|--victimplay-max-gpus) MAX_VICTIMPLAY_GPUS=$2; shift ;;
    -c|--curriculum) CURRICULUM=$2; shift ;;
    --lr-scale) LR_SCALE=$2; shift ;;
    -p|--predictor) USE_PREDICTOR=1 ;;
    --predictor-warmstart-ckpt) PREDICTOR_WARMSTART_CKPT=$2; shift ;;
    -r|--resume) RESUME_TIMESTAMP=$2; shift ;;
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

if [ -n "${USE_PREDICTOR}" ]; then
  PREDICTOR_FLAG="-p $RUN_NAME/predictor"
  VICTIMPLAY_CMD="/go_attack/kubernetes/victimplay-predictor.sh"

  # shellcheck disable=SC2215,SC2086,SC2089,SC2090
  ctl job run --container \
      "$PYTHON_IMAGE" \
      "$PYTHON_IMAGE" \
      $VOLUME_FLAGS \
      --command "/go_attack/kubernetes/shuffle-and-export.sh $RUN_NAME $RUN_NAME/predictor $VOLUME_NAME" \
      "/go_attack/kubernetes/train.sh $RUN_NAME/predictor $VOLUME_NAME $PREDICTOR_WARMSTART_CKPT" \
      --high-priority \
      --gpu 0 1 \
      --name go-training-"$1"-predictor
else
  VICTIMPLAY_CMD="/go_attack/kubernetes/victimplay.sh"
fi

# shellcheck disable=SC2215,SC2086,SC2089,SC2090
~/sleipnir/ctl/ctl/ctl.py job run --container \
    "$CPP_IMAGE" \
    "$CPP_IMAGE" \
    "$PYTHON_IMAGE" \
    "$PYTHON_IMAGE" \
    "$PYTHON_IMAGE" \
    $VOLUME_FLAGS \
    --command "$VICTIMPLAY_CMD $RUN_NAME $VOLUME_NAME" \
    "/engines/KataGo-custom/cpp/evaluate_loop.sh $PREDICTOR_FLAG /$VOLUME_NAME/victimplay/$RUN_NAME /$VOLUME_NAME/victimplay/$RUN_NAME/eval" \
    "/go_attack/kubernetes/train.sh $RUN_NAME $VOLUME_NAME $LR_SCALE" \
    "/go_attack/kubernetes/shuffle-and-export.sh $RUN_NAME $RUN_NAME $VOLUME_NAME" \
    "/go_attack/kubernetes/curriculum.sh $RUN_NAME $VOLUME_NAME $CURRICULUM" \
    --high-priority \
    --gpu 1 1 1 0 0 \
    --name go-train-"$1"-vital \
    --shared-host-dir-slow-tolerant \
    --replicas "${MIN_VICTIMPLAY_GPUS}" 1 1 1 1

EXTRA_VICTIMPLAY_GPUS=$((MAX_VICTIMPLAY_GPUS-MIN_VICTIMPLAY_GPUS))
if [ $EXTRA_VICTIMPLAY_GPUS -gt 0 ]; then
  # shellcheck disable=SC2086
  ~/sleipnir/ctl/ctl/ctl.py job run --container \
      "$CPP_IMAGE" \
      $VOLUME_FLAGS \
      --command "$VICTIMPLAY_CMD $RUN_NAME $VOLUME_NAME" \
      --gpu 1 \
      --name go-train-"$1"-extra \
      --shared-host-dir-slow-tolerant \
      --replicas "${EXTRA_VICTIMPLAY_GPUS}"
fi
