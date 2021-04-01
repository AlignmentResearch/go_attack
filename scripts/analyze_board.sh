#!/bin/bash

# CUDA_VISIBLE_DEVICES=1 ./scripts/analyze_board.sh -m white_win-1600

# Variables
ROOT=$( dirname $( dirname $( realpath "$0"  ) ) )
FILEDIR="$ROOT/analysis_logs"
MSG="empty"

# Help function
help () {
  echo "./analyze_board.sh "
  exit 0
}

# Taking arguments
POSITIONAL=()
while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -m | --msg)
    MSG="$2"
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

# Building analysis directory
mkdir -p $FILEDIR/$MSG

# diverting gtp log to the exp directory
rm -rf $FILEDIR/$MSG/analysis.cfg 
echo "logMessage = $MSG" >> "$FILEDIR/$MSG/analysis.cfg"
echo "logDir = /goattack/analysis_logs/$MSG  # Each run of KataGo will log to a separate file in this dir" \
>> "$FILEDIR/$MSG/analysis.cfg"

cat "$ROOT/configs/katago/analysis_custom.cfg" >> "$FILEDIR/$MSG/analysis.cfg"

# recording the shell command
echo "$ROOT/engines/KataGo-custom/cpp/katago analysis -config $FILEDIR/$MSG/analysis.cfg -model $ROOT/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz " \ 
> "$FILEDIR/$MSG/analysis.log"

$ROOT/engines/KataGo/cpp/katago analysis \
-config $FILEDIR/$MSG/analysis.cfg \
-model $ROOT/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz 