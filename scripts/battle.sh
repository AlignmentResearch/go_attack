#!/bin/bash

# CUDA_VISIBLE_DEVICES=0,1 ./scripts/battle.sh -e test -t 2 -n 2 -o -b gtp_black.cfg -w gtp_white.cfg

# Variables
ROOT=$( dirname $( dirname $( realpath "$0"  ) ) )
FILEDIR="$ROOT/games"
NUM="2"
THREADS="1"
CONFIG_PATH="$ROOT/configs/katago/gtp_example.cfg"
OPENING=0
ALTER=0

# Help function
help () {
  echo "./battle.sh -e for experiment name; -t for number of threads; 
  -b for black config name; -w for white config name;
  -n for number of games; -a for alternating colors; -o for loading openings."
  exit 0
}

# Taking arguments
POSITIONAL=()
while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -e | --exp)
    EXP="$2"
    EXPDIR="$FILEDIR/$EXP"
    shift # past argument
    shift # past value
    ;;
    -n | --num)
    NUM="$2"
    shift # past argument
    shift # past value
    ;;
    -b | --black)
    BLACK_CONFIG_NAME="$2"
    BLACK_CONFIG_PATH=$( dirname "${CONFIG_PATH}" )
    BLACK_CONFIG_PATH+="/$BLACK_CONFIG_NAME"
    shift # past argument
    shift # past value
    ;;
    -w | --white)
    WHITE_CONFIG_NAME="$2"
    WHITE_CONFIG_PATH=$( dirname "${CONFIG_PATH}" )
    WHITE_CONFIG_PATH+="/$WHITE_CONFIG_NAME"
    shift # past argument
    shift # past value
    ;;
    -t | --threads)
    THREADS="$2"
    shift # past argument
    shift # past value
    ;;
    -a | --alternate)
    ALTER=1
    shift # past argument
    ;;
    -o | --opening)
    OPENING=1
    shift # past argument
    ;;
    -h | --help)
    help
    ;;
    *)  # unknown option
    POSITIONAL+=("$1") # save it in an array for later
    shift
    ;;
esac
done
set -- "${POSITIONAL[@]}" # restore positional parameters

# Building experiment directory
FILENAME="$EXPDIR/game"
mkdir -p $EXPDIR

# diverting gtp log to the exp directory
rm -rf $EXPDIR/gtp_logs $EXPDIR/black.cfg $EXPDIR/white.cfg
echo "logDir = $EXPDIR/gtp_logs    # Each run of KataGo will log to a separate file in this dir" \
  >> "$EXPDIR/black.cfg"
echo "logDir = $EXPDIR/gtp_logs    # Each run of KataGo will log to a separate file in this dir" \
  >> "$EXPDIR/white.cfg"
cat $BLACK_CONFIG_PATH >> $EXPDIR/black.cfg
cat $WHITE_CONFIG_PATH >> $EXPDIR/white.cfg

# Set BLACK and WHITE
BLACK="$ROOT/engines/KataGo/cpp/katago gtp "
BLACK+="-config $EXPDIR/black.cfg "
BLACK+="-model $ROOT/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz"

WHITE="$ROOT/engines/KataGo/cpp/katago gtp "
WHITE+="-config $EXPDIR/white.cfg "
WHITE+="-model $ROOT/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz"

# -model $ROOT/models/kata1-b40c256-s7170990080-d1739777328.bin.gz
# -model $ROOT/models/g170-b10c128-s197428736-d67404019.bin.gz
# -model $ROOT/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz
# -model $ROOT/models/g170e-b20c256x2-s5303129600-d1228401921.bin.gz

ARGS="-size 19 "
ARGS+="-sgffile $FILENAME "
ARGS+="-games $NUM "
ARGS+="-threads $THREADS "
ARGS+="-auto -verbose "

if [[ $ALTER -eq 1 ]]
then
  ARGS+="-alternate "
fi

if [[ $OPENING -eq 1 ]]
then
  ARGS+="-openings $ROOT/openings/ "
fi

# recording the shell command
echo "$ROOT/controllers/gogui/bin/gogui-twogtp -black "$BLACK" -white "$WHITE" $ARGS" > "$EXPDIR/game.log"

# adding experiment name to to_analyze.txt
echo "$EXP" >> "$( dirname $EXPDIR )/finished_exp.txt"

bash $ROOT/controllers/gogui/bin/gogui-twogtp -black "$BLACK" -white "$WHITE" $ARGS

