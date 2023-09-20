#!/bin/bash -e
cd /engines/KataGo-custom/python

# Command line flag parsing (https://stackoverflow.com/a/33826763/4865149).
# Flags must be specified before positional arguments.
while [ -n "${1-}" ]; do
  case $1 in
    # Whether to copy model for warmstarting. If this flag is used,
    # --initial-weights flag should be specified as well.
    # For predictor training, this flag should not be specified since the
    # curriculum script will handle copying the victim models for the predictor.
    --copy-initial-model) COPY_INITIAL_MODEL=1; ;;
    # Path to directory of TF weights for warmstarting.
    --initial-weights) INITIAL_WEIGHTS=$2; shift ;;
    -*) echo "Unknown parameter passed: $1"; usage; exit 1 ;;
    *) break ;;
  esac
  shift
done

RUN_NAME="$1"
VOLUME_NAME="$2"
LR_SCALE="$3"

EXPERIMENT_DIR=/"$VOLUME_NAME"/victimplay/"$RUN_NAME"
if [ ! -e "$EXPERIMENT_DIR/selfplay/prev-selfplay" ]; then
  mkdir -p "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  mkdir -p "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2

  ln -s /shared/katago-training-data/20220301-to-20220624 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/katago-20220301-to-20220624

  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s0-d0 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s1069312-d108621833 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s2139392-d108716292 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s3067392-d108989510 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s4066048-d109192193 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s4992000-d109448047 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s5919488-d109695062 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s6846464-d110008854 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s7845120-d110174950 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s8843008-d110453096 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s9769728-d110671271 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s10838784-d110976447 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s11909632-d111164244 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s12977664-d111499426 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s14046464-d111673247 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s15044096-d111963943 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s16113664-d112216121 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s17114112-d112481685 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s18112512-d112719203 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s19038976-d112928359 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s19966720-d113183621 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s20963840-d113470477 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s22032896-d113718824 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s23030528-d113901055 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s24027648-d114193083 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s25025792-d114452501 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s25881088-d114745057 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s26809344-d114890123 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s27807232-d115179490 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s28946944-d115472217 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s30015488-d115744118 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s30872064-d115990848 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s31941888-d116156761 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s32940288-d116481152 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s33868288-d116725030 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s34865664-d116998994 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s35865088-d117212838 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s37005568-d117491164 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s37934080-d117741583 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s39002880-d117939685 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s40073216-d118291965 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s41000704-d118391965 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s41997824-d118716341 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s42996224-d118891702 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s43922176-d119149888 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s44850176-d119458264 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s45849344-d119720023 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s46846976-d119997107 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s47916288-d120246240 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s48984320-d120474993 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s49983488-d120672761 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s50981120-d120934797 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s51836416-d121200469 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s52978176-d121455102 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s54049024-d121731880 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s55046656-d121908729 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s56114432-d122222742 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s56969728-d122396736 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s57897984-d122713840 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s58967040-d123001552 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1
  ln -s /shared/victimplay/ttseng-cp505-advtrain-spp082-lr01-20230728-170008/iteration-0/selfplay/t0-s60035840-d123151552 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h1

  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s0-d0 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s1070336-d123667555 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s2068224-d123848035 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s3066112-d124048035 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s4065024-d124291741 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s5063936-d124619911 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s6133504-d124941582 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s7203584-d125144349 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s8272640-d125273982 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s9341696-d125652695 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s10482432-d125914999 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s11409664-d126101696 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s12336384-d126311809 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s13334272-d126550041 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s14403328-d126856720 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s15401728-d127103840 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s16327936-d127293063 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s17325568-d127637081 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s18324480-d127821626 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s19394304-d128131178 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s20390912-d128408754 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
  ln -s /shared/victimplay/ttseng-cp505-h2-20230823-142646/iteration-0/selfplay/t0-s21460736-d128614571 "$EXPERIMENT_DIR"/selfplay/prev-selfplay/h2
fi

if [ -z "$INITIAL_WEIGHTS" ]; then
    echo "No initial weights specified, using random weights"
    MODEL_KIND=b6c96
else
    echo "Using initial weights: $INITIAL_WEIGHTS"
    # The train script will use the model kind specified by the warmstarted
    # model's config. MODEL_KIND is ignored.
    MODEL_KIND="unused"

    if [ ! -d "$INITIAL_WEIGHTS" ]; then
        echo "Error: initial weights do not exist: $INITIAL_WEIGHTS"
        exit 1
    fi
    mkdir -p "$EXPERIMENT_DIR"/train/t0/initial_weights
    cp "$INITIAL_WEIGHTS"/saved_model/model.config.json "$EXPERIMENT_DIR"/train/t0/model.config.json
    cp -r "$INITIAL_WEIGHTS"/saved_model/variables/* "$EXPERIMENT_DIR"/train/t0/initial_weights

    if [ -n "${COPY_INITIAL_MODEL:-}" ] &&
       [ ! -f "$EXPERIMENT_DIR"/done-copying-warmstart-model ]; then
      INITIAL_MODEL=""
      ADV_MODEL="$INITIAL_WEIGHTS/model.bin.gz"
      if [ -f "$ADV_MODEL" ]; then
          # If the warmstart model is an adversary, then we expect model.bin.gz to
          # exist in $INITIAL_WEIGHTS.
          INITIAL_MODEL="$ADV_MODEL"
      else
          # Warmstart model is a victim, so we search $VICTIM_MODELS_DIR for the
          # victim model.
          VICTIM_MODELS_DIR=/"$VOLUME_NAME"/victims
          INITIAL_WEIGHTS_BASENAME=$(basename "$INITIAL_WEIGHTS")
          POSSIBLE_MODEL_NAMES=(\
              "kata1-$INITIAL_WEIGHTS_BASENAME.txt.gz"
              "kata1-$INITIAL_WEIGHTS_BASENAME.bin.gz"
              "$INITIAL_WEIGHTS_BASENAME.bin.gz"
          )
          for POSSIBLE_NAME in "${POSSIBLE_MODEL_NAMES[@]}"; do
              POSSIBLE_MODEL="$VICTIM_MODELS_DIR/$POSSIBLE_NAME"
              if [ -f "$POSSIBLE_MODEL" ]; then
                  INITIAL_MODEL="$POSSIBLE_MODEL"
                  break
              fi
          done
      fi
      if [ -z "$INITIAL_MODEL" ]; then
          echo "Error: initial weights exist at $INITIAL_WEIGHTS_DIR, but no"\
               "matching model was found."
          exit 1
      fi
      echo "Using initial model: $INITIAL_MODEL"
      MODEL_EXTENSION=${INITIAL_MODEL: -6} # bin.gz or txt.gz
      TARGET_DIR="$EXPERIMENT_DIR"/models/t0-s0-d0
      mkdir -p "$TARGET_DIR"/saved_model
      cp "$INITIAL_MODEL" "$TARGET_DIR"/model."$MODEL_EXTENSION"
      # Copying the saved_model files isn't strictly necessary, but we copy them
      # in case we want to warmstart from this t0-s0-d0/ in a different run.
      cp "$INITIAL_WEIGHTS"/saved_model/model.config.json "$TARGET_DIR"/saved_model
      cp -r "$INITIAL_WEIGHTS"/saved_model/variables "$TARGET_DIR"/saved_model
      touch "$EXPERIMENT_DIR"/done-copying-warmstart-model
    fi
fi

./selfplay/train.sh "$EXPERIMENT_DIR" t0 "$MODEL_KIND" 256 main -disable-vtimeloss -lr-scale "$LR_SCALE" -max-train-bucket-per-new-data 4
