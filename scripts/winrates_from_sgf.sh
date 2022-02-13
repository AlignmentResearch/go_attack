#!/bin/bash

OUR_MODEL=${OUR_MODEL:-chai}

echo "Wins as white"
grep -E "PW\[${OUR_MODEL}\].*result=W+" "$@" | wc -l
echo "Wins as black"
grep -E "PB\[${OUR_MODEL}\].*result=B+" "$@" | wc -l
echo "Draws"
grep -E ".*result=0" "$@" | wc -l
echo "Losses as white"
grep -E "PW\[${OUR_MODEL}\].*result=B+" "$@" | wc -l
echo "Losses as black"
grep -E "PB\[${OUR_MODEL}\].*result=W+" "$@" | wc -l

