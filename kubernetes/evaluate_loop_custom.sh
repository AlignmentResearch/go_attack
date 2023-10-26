#!/bin/bash -eu

usage() {
    echo "Usage: $0 [--victim-list VICTIM_LIST] [-victim-dir VICTIM_DIR]"
    echo "          [--prediction-dir PREDICTOR_DIR] [--katago-bin KATAGO_BIN]"
    echo "          [--go-attack-root GO_ATTACK_ROOT] BASE_DIR OUTPUT_DIR"
    echo
    echo "positional arguments:"
    echo " BASE_DIR The root of the training run, containing selfplay data, models and"
    echo " related directories."
    echo " OUTPUT_DIR The directory to output results to."
    echo
    echo "optional arguments:"
    echo "  --config CONFIG"
    echo "    KataGo match config."
    echo "    Default: GO_ATTACK_ROOT/configs/match-1gpu.cfg"
    echo "  -v VICTIM_LIST, --victim-list VICTIM_LIST"
    echo "    A comma-separated list of models in VICTIM_DIR to use."
    echo "    If empty, the most recent model will be used."
    echo "  -d VICTIM_DIR, --victim-dir VICTIM_DIR"
    echo "    The directory containing the victim models."
    echo "    Default: BASE_DIR/victims"
    echo "  -p PREDICTOR_DIR, --prediction-dir PREDICTOR_DIR"
    echo "    The path containing predictor models, if applicable."
    echo "  -k KATAGO_BIN, --katago-bin KATAGO_BIN"
    echo "    The path to the KataGo binary."
    echo "    Default: '/engines/KataGo-custom/cpp/katago'"
    echo "  -g GO_ATTACK_ROOT, --go-attack-root GO_ATTACK_ROOT"
    echo "    The root directory of the go-attack repository."
    echo "    Default: '/go_attack'"
    echo
    echo "Optional arguments should be specified before positional arguments."
    echo "Currently expects to be run from within the 'cpp' directory of the KataGo repo."
}

PREDICTOR_DIR=""
KATAGO_BIN="/engines/KataGo-custom/cpp/katago"
GO_ATTACK_ROOT="/go_attack"

# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while [ -n "${1-}" ]; do
  case $1 in
    -h|--help) usage; exit 0 ;;
    --config) CONFIG="$2"; shift 2 ;;
    -p|--prediction-dir) PREDICTOR_DIR="$2"; shift 2 ;;
    -k|--katago-bin) KATAGO_BIN="$2"; shift 2 ;;
    -g|--go-attack-root) GO_ATTACK_ROOT="$2"; shift 2 ;;
    -*) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
    *) break ;;
  esac
done
CONFIG=${CONFIG:-"$GO_ATTACK_ROOT"/configs/match-1gpu.cfg}

NUM_POSITIONAL_ARGUMENTS=3
if [ $# -ne ${NUM_POSITIONAL_ARGUMENTS} ]; then
  echo "Wrong number of positional arguments. Expected ${NUM_POSITIONAL_ARGUMENTS}, got $#"
  echo "Positional arguments: $@"
  usage
  exit 1
fi

BASE_DIR="$1"
MODELS_DIR="$BASE_DIR"/models
OUTPUT_DIR="$2"
# Play against a KataGo network to make sure that the trained model is gaining
# competence at playing Go.
# This network should be manually changed periodically when the trained model
# becomes stronger than it.
COMPARISON_MODEL_PATH="$3"
mkdir -p "$OUTPUT_DIR"/logs
mkdir -p "$OUTPUT_DIR"/sgfs

LAST_STEP=-1
SLEEP_INTERVAL=30
while true
do
    if [[ ! -d "$MODELS_DIR" ]]
    then
        echo "Waiting for $MODELS_DIR to exist..."
        sleep 10
        continue
    fi

    LATEST_MODEL_DIR=$(ls -v "$MODELS_DIR" | grep "\-s[0-9]\+" | tail --lines 1)

    if [[ -z "$LATEST_MODEL_DIR" ]]; then
        echo "Waiting for a model to exist..."
        sleep $SLEEP_INTERVAL
        continue
    fi

    if [[ "$LATEST_MODEL_DIR" =~ -s([0-9]+) ]]; then
        # The first capture group is the step number
        STEP=${BASH_REMATCH[1]}

        # Have we evaluated this model yet?
        if [ "$STEP" -gt "$LAST_STEP" ]; then

            # Run the evaluation
            echo "Evaluating model $LATEST_MODEL_DIR"
            $KATAGO_BIN match \
                -config "$CONFIG" \
                -config "/go_attack/configs/eval.cfg" \
                -override-config nnModelFile0="$COMPARISON_MODEL_PATH" \
                -override-config botName0="$(basename ${COMPARISON_MODEL_PATH})" \
                -override-config nnModelFile1="$MODELS_DIR"/"$LATEST_MODEL_DIR"/model.pt \
                -override-config botName1="$LATEST_MODEL_DIR" \
                -sgf-output-dir "$OUTPUT_DIR"/sgfs/"$LATEST_MODEL_DIR" \
                2>&1 | tee "$OUTPUT_DIR"/logs/"$LATEST_MODEL_DIR".log

            # Update the last step
            LAST_STEP="$STEP"
        fi
    fi
    sleep $SLEEP_INTERVAL
done
