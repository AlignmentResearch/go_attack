#!/bin/bash -eu
# shellcheck disable=SC2001

OUTPUT_DIR=$1

CP505_NAME=kata1-b40c256-s11840935168-d2898845681
CP127_NAME=kata1-b20c256x2-s5303129600-d1228401921

/go_attack/kubernetes/log-git-commit.sh "$OUTPUT_DIR"

python3 go_attack/scripts/baseline_attack.py \
  --config go_attack/configs/gtp-base.cfg \
  --models /shared/victims/"$CP505_NAME".bin.gz \
    /shared/victims/"$CP127_NAME".bin.gz \
  --num-games 150 \
  --policy edge mirror spiral random \
  --num-visits 1 2 4 8 16 32 \
  --passing-behavior standard avoid-pass-alive-territory \
  --victim-color B W \
  --moves-before-pass 800 \
  --parallel-runs-per-gpu 12 \
  --log-dir "$OUTPUT_DIR"/original

# Rescore the results using KataGo scoring.
mkdir -p "$OUTPUT_DIR/rescored"
for DIR in "$OUTPUT_DIR/original/"*; do
  MODEL=$(echo "$DIR" | sed "s/.*model=\([a-z0-9-]\+\).*/\1/")
  VISITS=$(echo "$DIR" | sed "s/.*visits=\([0-9]\+\).*/\1/")
  POLICY=$(echo "$DIR" | sed "s/.*policy=\([a-z]\+\).*/\1/")
  VICTIM_COLOR=$(echo "$DIR" | sed "s/.*victim=\([A-Z]\).*/\1/")
  PASSING_BEHAVIOR=$(echo "$DIR" | sed "s/.*pass=\([a-z\-]\+\).*/\1/")
  if [ "$MODEL" = "$CP505_NAME" ]; then
    VICTIM=cp505
  elif [ "$MODEL" = "$CP127_NAME" ]; then
    VICTIM=cp127
  else
    echo "Unknown model: $MODEL"
    exit 1
  fi
  if [ "$PASSING_BEHAVIOR" = "avoid-pass-alive-territory" ]; then
    VICTIM+=h
  fi
  VICTIM+="-v${VISITS}-${VICTIM_COLOR}"
  echo "policy: $POLICY, victim: $VICTIM"
  python3 /go_attack/scripts/score_with_katago.py \
    --executable /engines/KataGo-raw/cpp/katago \
    --output "$OUTPUT_DIR/rescored/${VICTIM}-vs-${POLICY}.sgfs" \
    "$DIR"
done
