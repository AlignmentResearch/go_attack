#!/bin/bash

# attack

# Variables
ROOT=$( dirname $( dirname $( realpath "$0"  ) ) )
FILEDIR="$ROOT/games"
NUM="2"
THREADS="1"
CONFIG_PATH="$ROOT/configs/katago/gtp_example.cfg"
ATTACK_PLA=""
SOFT_ATTACK="0"
SOFT_BACKUP="-1"
ATK_EXPAND="false"
MINIMAX_SB="false"

OPENING=0
ALTER=0
FORCE=0
BLACK_PLAYOUTS="1600"
WHITE_PLAYOUTS="1600"
SIZE="19"
KOMI="7.5"
GPU="1"

# Help function
help () {
  echo "./attack.sh -e for experiment name; -t for number of threads; -p for attack player;
  -b for black config name; -w for white config name; -f for force; 
  -n for number of games; -a for alternating colors; -o for loading openings;
  --size for board size; --komi for komi."
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
    -p | --player)
    ATTACK_PLA="$2"
    shift # past argument
    shift # past value
    ;;
    -sa | --soft_attack)
    SOFT_ATTACK="$2"
    shift # past argument
    shift # past value
    ;;
    -sb | --soft_backup)
    SOFT_BACKUP="$2"
    shift # past argument
    shift # past value
    ;;
    -n | --num)
    NUM="$2"
    shift # past argument
    shift # past value
    ;;
    -f | --force)
    FORCE=1
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
    -bp | --black_playouts)
    BLACK_PLAYOUTS="$2"
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
    -wp | --white_playouts)
    WHITE_PLAYOUTS="$2"
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
    -ae | --attack_expand)
    ATK_EXPAND="true"
    shift # past argument
    ;;
    -ms | --minimax_softbackup)
    MINIMAX_SB="true"
    shift # past argument
    ;;
    --size)
    SIZE="$2"
    shift # past argument
    shift # past value
    ;;
    --komi)
    KOMI="$2"
    shift # past argument
    shift # past value
    ;;
    --gpu)
    GPU="$2"
    shift # past argument
    shift # past value
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

# if using -f flag, deleting the whole exp directory
if [[ $FORCE -eq 1 ]]
then
  rm -rf $EXPDIR
fi

# Building experiment directory
FILENAME="$EXPDIR/game"
mkdir -p $EXPDIR

# removing previous configs
rm -rf $EXPDIR/gtp_logs $EXPDIR/black.cfg $EXPDIR/white.cfg

# Set BLACK and WHITE
BLACK=""
if [[ "$ATTACK_PLA" == "black" ]]
then
  BLACK+="$ROOT/engines/KataGo-custom/cpp/katago gtp "
  echo "visitsThreshold2Attack = ${SOFT_ATTACK}    # Soft threshold to apply soft attack"  >> "$EXPDIR/black.cfg"
  echo "optimismThreshold4Backup = ${SOFT_BACKUP}    # Optimism threshold to apply soft attack"  >> "$EXPDIR/black.cfg"
  echo "attackExpand = ${ATK_EXPAND}    # Tree expansion according to attack value"  >> "$EXPDIR/black.cfg"
  echo "isMinimaxOptim4Backup = ${MINIMAX_SB}    # is minimax soft backup"  >> "$EXPDIR/black.cfg"
  echo "attackPla = BLACK    # black player as the attack player"  >> "$EXPDIR/black.cfg"
else
  BLACK+="$ROOT/engines/KataGo-custom/cpp/katago gtp "
fi
BLACK+="-config $EXPDIR/black.cfg "
BLACK+="-model $ROOT/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz"

WHITE=""
if [[ "$ATTACK_PLA" == "white" ]]
then
  WHITE+="$ROOT/engines/KataGo-custom/cpp/katago gtp "
  echo "visitsThreshold2Attack = ${SOFT_ATTACK}    # Soft threshold to apply soft attack"  >> "$EXPDIR/white.cfg"
  echo "optimismThreshold4Backup = ${SOFT_BACKUP}    # Optimism threshold to apply soft attack"  >> "$EXPDIR/white.cfg"
  echo "attackExpand = ${ATK_EXPAND}    # Tree expansion according to attack value"  >> "$EXPDIR/white.cfg"
  echo "isMinimaxOptim4Backup = ${MINIMAX_SB}    # is minimax soft backup"  >> "$EXPDIR/white.cfg"
  echo "attackPla = WHITE    # white player as the attack player"  >> "$EXPDIR/white.cfg"
else
  WHITE+="$ROOT/engines/KataGo-custom/cpp/katago gtp "
fi
WHITE+="-config $EXPDIR/white.cfg "
WHITE+="-model $ROOT/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz"

# -model $ROOT/models/kata1-b40c256-s7170990080-d1739777328.bin.gz
# -model $ROOT/models/g170-b10c128-s197428736-d67404019.bin.gz
# -model $ROOT/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz
# -model $ROOT/models/g170e-b20c256x2-s5303129600-d1228401921.bin.gz

# diverting gtp log to the exp directory
echo "logDir = $EXPDIR/gtp_logs    # Each run of KataGo will log to a separate file in this dir" >> "$EXPDIR/black.cfg"
echo "logDir = $EXPDIR/gtp_logs    # Each run of KataGo will log to a separate file in this dir" >> "$EXPDIR/white.cfg"
echo "jsonDir = $EXPDIR/data_logs" >> "$EXPDIR/black.cfg"
echo "jsonDir = $EXPDIR/data_logs" >> "$EXPDIR/white.cfg"
echo "maxPlayouts = $BLACK_PLAYOUTS " >> "$EXPDIR/black.cfg"
echo "maxPlayouts = $WHITE_PLAYOUTS " >> "$EXPDIR/white.cfg"

if [[ $GPU -lt 1 ]]
then
echo "Number of GPUs cannot be less than 1"
else
  echo "numNNServerThreadsPerModel = $GPU" >> "$EXPDIR/black.cfg"
  echo "numNNServerThreadsPerModel = $GPU" >> "$EXPDIR/white.cfg"
  for ((i = 0 ; i < $GPU ; i++)); do
    echo "cudaDeviceToUseThread${i} = ${i}" >> "$EXPDIR/black.cfg"
    echo "cudaDeviceToUseThread${i} = ${i}" >> "$EXPDIR/white.cfg"
  done
fi
cat $BLACK_CONFIG_PATH >> $EXPDIR/black.cfg
cat $WHITE_CONFIG_PATH >> $EXPDIR/white.cfg


ARGS="-size $SIZE "
ARGS+="-komi $KOMI "
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
echo "Key Shell Commands for the game: " > "$EXPDIR/game.log"
echo "BLACK=\"${BLACK}\"" >> "$EXPDIR/game.log"
echo "WHITE=\"${WHITE}\"" >> "$EXPDIR/game.log"
echo "$ROOT/controllers/gogui/bin/gogui-twogtp -black \$BLACK -white \$WHITE $ARGS" >> "$EXPDIR/game.log"

# make each codebase first
cd $ROOT/engines/KataGo-custom/cpp && make && pwd
# cd $ROOT/engines/KataGo-raw/cpp && make && pwd

bash $ROOT/controllers/gogui/bin/gogui-twogtp -black "$BLACK" -white "$WHITE" $ARGS

