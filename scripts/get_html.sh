#!/bin/bash

# ./scripts/get_html.sh -f finished_exp.txt

# Variables
ROOT=$( dirname $( dirname $( realpath "$0"  ) ) )
EXP=""
FILE=""

# Help function
help () {
  echo "./get_html.sh -e for experiment name; ."
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
    shift # past argument
    shift # past value
    ;;
    -f | --file)
    FILE="$2"
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

if [ ! -z "$EXP" ]
then
    bash $ROOT/controllers/gogui-1.5.1/bin/gogui-twogtp -analyze $ROOT/games/$EXP/game.dat      
fi

if [ ! -z "$FILE" ]
then
while read line 
do
echo "Getting HTML files from $line ..."
bash $ROOT/controllers/gogui-1.5.1/bin/gogui-twogtp -analyze $ROOT/games/$line/game.dat -force
done < $ROOT/games/$FILE
fi