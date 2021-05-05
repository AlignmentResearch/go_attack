# CUDA_VISIBLE_DEVICES=0,1,2 /goattack/scripts/attack.sh -p black -st 800 -e b40vb40-st800-w1600b_atk1600-full -t 1 -n 50 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 3

# THRESHOLD2
# CUDA_VISIBLE_DEVICES=0,1,2,3 /goattack/scripts/attack.sh -p black -st 0 -st2 50 -e optimism-soft-attack-50test-9x9 -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 9 --komi 7 --gpu 4
# CUDA_VISIBLE_DEVICES=0,1,2,3 /goattack/scripts/attack.sh -p black -st 0 -st2 100 -e optimism-soft-attack-100test-9x9 -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 9 --komi 7 --gpu 4
# CUDA_VISIBLE_DEVICES=0,1,2,3 /goattack/scripts/attack.sh -p black -st 0 -st2 200 -e optimism-soft-attack-200test-9x9 -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 9 --komi 7 --gpu 4
# CUDA_VISIBLE_DEVICES=0,1,2,3 /goattack/scripts/attack.sh -p black -st 0 -st2 400 -e optimism-soft-attack-400test-9x9 -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 9 --komi 7 --gpu 4

# CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black -st 0 -st2 100 -e optimism-soft-attack-19x19 -t 1 -n 50 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 3

# simple battle
# CUDA_VISIBLE_DEVICES=0,1 /goattack/scripts/attack.sh -e test-battle -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 100 -wp 100 --size 19 --komi 7.5 --gpu 2
# CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -e komi7.5baseline-w1600b1600-full -t 1 -n 50 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 3 -f
# CUDA_VISIBLE_DEVICES=0,1 /goattack/scripts/attack.sh -e komi7.0baseline-w1600b1600-9x9 -t 1 -n 50 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 9 --komi 7.0 --gpu 2

# Attack Using Utilities

# CUDA_VISIBLE_DEVICES=1 /goattack/scripts/attack.sh -p black -st 999999 -st2 0 -e custom-code-battle-check-19x19 -t 1 -n 20 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 1

# Attack Expansion
# CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black -st 0 -st2 0 -e b40vb40-st0-w1600b_atk1600-atkexpand-o-19x19 -o -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 3 -f
# CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black -st 800 -st2 0 -e b40vb40-st800-w1600b_atk1600-atkexpand-o-19x19 -o -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 3 -f

# CUDA_VISIBLE_DEVICES=3 /goattack/scripts/attack.sh -p black -st 800 -st2 0 -e b40vb40-st800-w1600b_atk1600-atkexpand-19x19 -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 1 -f
CUDA_VISIBLE_DEVICES=0,1,2 /goattack/scripts/attack.sh -p black -st 400 -st2 0 -e b40vb40-st400-w1600b_atk1600-atkexpand-19x19 -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 3 -f
CUDA_VISIBLE_DEVICES=0,1,2 /goattack/scripts/attack.sh -p black -st 0 -st2 50 -e b40vb40-optimst50-w1600b_atk1600-atkexpand-19x19 -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 3 -f
CUDA_VISIBLE_DEVICES=0,1,2 /goattack/scripts/attack.sh -p black -st 200 -st2 0 -e b40vb40-st200-w1600b_atk1600-atkexpand-19x19 -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 3 -f
CUDA_VISIBLE_DEVICES=0,1,2 /goattack/scripts/attack.sh -p black -st 0 -st2 100 -e b40vb40-optimst100-w1600b_atk1600-atkexpand-19x19 -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 3 -f
CUDA_VISIBLE_DEVICES=0,1,2 /goattack/scripts/attack.sh -p black -st 100 -st2 0 -e b40vb40-st100-w1600b_atk1600-atkexpand-19x19 -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 3 -f
CUDA_VISIBLE_DEVICES=0,1,2 /goattack/scripts/attack.sh -p black -st 0 -st2 200 -e b40vb40-optimst200-w1600b_atk1600-atkexpand-19x19 -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 3 -f
# CUDA_VISIBLE_DEVICES=0,1,2 /goattack/scripts/attack.sh -p black -st 1200 -st2 0 -e b40vb40-st1200-w1600b_atk1600-atkexpand-19x19 -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 3 -f
# CUDA_VISIBLE_DEVICES=0,1,2 /goattack/scripts/attack.sh -p black -st 0 -st2 0 -e b40vb40-st0-w1600b_atk1600-atkexpand-19x19 -t 1 -n 10 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 --size 19 --komi 7.5 --gpu 3 -f
