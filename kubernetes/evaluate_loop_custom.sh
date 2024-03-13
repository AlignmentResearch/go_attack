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

VICTIM_LIST_ARG=""
VICTIMS_DIR=""
PREDICTOR_DIR=""
KATAGO_BIN="/engines/KataGo-custom/cpp/katago"
GO_ATTACK_ROOT="/go_attack"

# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149)
while [ -n "${1-}" ]; do
  case $1 in
    -h|--help) usage; exit 0 ;;
    --config) CONFIG="$2"; shift 2 ;;
    -v|--victim-list) VICTIM_LIST_ARG="$2"; shift 2 ;;
    -d|--victim-dir) VICTIMS_DIR="$2"; shift 2 ;;
    -p|--prediction-dir) PREDICTOR_DIR="$2"; shift 2 ;;
    -k|--katago-bin) KATAGO_BIN="$2"; shift 2 ;;
    -g|--go-attack-root) GO_ATTACK_ROOT="$2"; shift 2 ;;
    -*) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
    *) break ;;
  esac
done
CONFIG=${CONFIG:-"$GO_ATTACK_ROOT"/configs/match-1gpu.cfg}

NUM_POSITIONAL_ARGUMENTS=2
if [ $# -ne ${NUM_POSITIONAL_ARGUMENTS} ]; then
  echo "Wrong number of positional arguments. Expected ${NUM_POSITIONAL_ARGUMENTS}, got $#"
  echo "Positional arguments: $@"
  usage
  exit 1
fi

BASE_DIR="$1"
MODELS_DIR="$BASE_DIR"/models
OUTPUT_DIR="$2"
mkdir -p "$OUTPUT_DIR"/logs
mkdir -p "$OUTPUT_DIR"/sgfs

if [ -z "$VICTIMS_DIR" ]; then
    VICTIMS_DIR="$BASE_DIR"/victims
fi

LAST_STEP=-1
SLEEP_INTERVAL=30
while true
do
    if [[ ! -d "$MODELS_DIR" || ! -d "$VICTIMS_DIR" ]]
    then
        echo "Waiting for $MODELS_DIR and $VICTIMS_DIR to exist..."
        sleep 10
        continue
    fi

    if [[ -z "$VICTIM_LIST_ARG" ]]
    then
        # https://stackoverflow.com/questions/1015678/get-most-recent-file-in-a-directory-on-linux
        VICTIM_LIST=$(ls -Art "$VICTIMS_DIR" | grep "\.gz" | tail --lines 1)
    else
        VICTIM_LIST="$VICTIM_LIST_ARG"
    fi

    # Split the string VICTIM_LIST into an array victim_array:
    # https://stackoverflow.com/a/10586169/7086623
    IFS=', ' read -r -a victim_array <<< "${VICTIM_LIST}"

    LATEST_MODEL_DIR=$(ls -v "$MODELS_DIR" | grep "\-s[0-9]\+" | tail --lines 1)

    if [[ -z "$LATEST_MODEL_DIR" || -z "$VICTIM_LIST" ]]; then
        echo "Waiting for an adversary and a victim to exist..."
        sleep $SLEEP_INTERVAL
        continue
    fi

    if [[ "$LATEST_MODEL_DIR" =~ -s([0-9]+) ]]; then
        # The first capture group is the step number
        STEP=${BASH_REMATCH[1]}

        # Have we evaluated this model yet?
        if [ "$STEP" -gt "$LAST_STEP" ]; then
            for VICTIM in "${victim_array[@]}"; do
                # https://stackoverflow.com/questions/12152626/how-can-i-remove-the-extension-of-a-filename-in-a-shell-script
                VICTIM_NAME=$(echo "$VICTIM" | cut -f 1 -d '.')

                if [ -n "$PREDICTOR_DIR" ]; then
                    # https://stackoverflow.com/questions/4561895/how-to-recursively-find-the-latest-modified-file-in-a-directory
                    PREDICTOR=$(find $PREDICTOR_DIR -name *.bin.gz -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -f2- -d" ")
                    EXTRA_CONFIG+=",predictorPath=$PREDICTOR"
                fi

                # Run the evaluation
                echo "Evaluating model $LATEST_MODEL_DIR against victim $VICTIM_NAME"
                $KATAGO_BIN match \
                    -config "$CONFIG" \
                    -config "$VICTIMS_DIR"/victim.cfg \
                    -config /go_attack/kubernetes/evaluate_loop_custom.cfg \
                    -override-config nnModelFile0="$VICTIMS_DIR"/"$VICTIM" \
                    -override-config botName0="victim-$VICTIM_NAME" \
                    -override-config nnModelFile1="$MODELS_DIR"/"$LATEST_MODEL_DIR"/model.bin.gz \
                    -override-config botName1="adv-$LATEST_MODEL_DIR-noresultneg" \
                    -sgf-output-dir "$OUTPUT_DIR"/sgfs/"$VICTIM_NAME"_"$LATEST_MODEL_DIR" \
                    2>&1 | tee "$OUTPUT_DIR"/logs/"$VICTIM_NAME"_"$LATEST_MODEL_DIR".log
            done
            # Update the last step
            LAST_STEP="$STEP"
        fi
    fi
    sleep $SLEEP_INTERVAL
done
