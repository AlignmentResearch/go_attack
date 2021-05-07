# Soft Attack
# [50, 100, 200, 400, 800, 1200, 1600]

# CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
#     -sa 50 -sb 0 -n 10 -e softatk/sa50-w1600b_atk1600-9x9 --size 9 --gpu 3 -f
    
# CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
#     -sa 100 -sb 0 -n 10 -e softatk/sa100-w1600b_atk1600-9x9 --size 9 --gpu 3 -f

# CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
#     -sa 200 -sb 0 -n 10 -e softatk/sa200-w1600b_atk1600-9x9 --size 9 --gpu 3 -f

# CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
#     -sa 400 -sb 0 -n 10 -e softatk/sa400-w1600b_atk1600-9x9 --size 9 --gpu 3 -f

# CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
#     -sa 800 -sb 0 -n 10 -e softatk/sa800-w1600b_atk1600-9x9 --size 9 --gpu 3 -f

# CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
#     -sa 1200 -sb 0 -n 10 -e softatk/sa1200-w1600b_atk1600-9x9 --size 9 --gpu 3 -f

# CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
#     -sa 1600 -sb 0 -n 10 -e softatk/sa1600-w1600b_atk1600-9x9 --size 9 --gpu 3 -f


# MCTS soft backup + Attack Expansion
# [50, 100, 200, 400, 800, 1200, 1600]

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 50 -ae -n 10 -e mctssb_atkexpand/mctssb50-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f
    
CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 100 -ae -n 10 -e mctssb_atkexpand/mctssb100-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 200 -ae -n 10 -e mctssb_atkexpand/mctssb200-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 400 -ae -n 10 -e mctssb_atkexpand/mctssb400-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 800 -ae -n 10 -e mctssb_atkexpand/mctssb800-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 1200 -ae -n 10 -e mctssb_atkexpand/mctssb1200-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 1600 -ae -n 10 -e mctssb_atkexpand/mctssb1600-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f


# Baselines
CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -n 10 -e baseline/komi7.0-w1600b1600-9x9 --size 9 --gpu 3 -f


# Attack Expansion Only

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 99999 -sb 0 -ae -n 10 -e atkexpand/w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f


# Soft Attack + Attack Expansion
# [0, 50, 100, 200, 400, 800, 1200, 1600]

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 0 -ae -n 10 -e softatk_atkexpand/sa0-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 50 -sb 0 -ae -n 10 -e softatk_atkexpand/sa50-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f
    
CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 100 -sb 0 -ae -n 10 -e softatk_atkexpand/sa100-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 200 -sb 0 -ae -n 10 -e softatk_atkexpand/sa200-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 400 -sb 0 -ae -n 10 -e softatk_atkexpand/sa400-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 800 -sb 0 -ae -n 10 -e softatk_atkexpand/sa800-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 1200 -sb 0 -ae -n 10 -e softatk_atkexpand/sa1200-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 1600 -sb 0 -ae -n 10 -e softatk_atkexpand/sa1600-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f


# Minimax soft backup + Attack Expansion
# [50, 100, 200, 400, 800, 1200, 1600]

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 50 -ms -ae -n 10 -e minimaxsb_atkexpand/minimaxsb50-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f
    
CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 100 -ms -ae -n 10 -e minimaxsb_atkexpand/minimaxsb100-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 200 -ms -ae -n 10 -e minimaxsb_atkexpand/minimaxsb200-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 400 -ms -ae -n 10 -e minimaxsb_atkexpand/minimaxsb400-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 800 -ms -ae -n 10 -e minimaxsb_atkexpand/minimaxsb800-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 1200 -ms -ae -n 10 -e minimaxsb_atkexpand/minimaxsb1200-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f

CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
    -sa 0 -sb 1600 -ms -ae -n 10 -e minimaxsb_atkexpand/minimaxsb1600-w1600b_atk1600-atkexpand-9x9 --size 9 --gpu 3 -f


# Tests and Debug

# CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh -p black --komi 7.5 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
#     -sa 100 -sb 0 -ae -n 10 -e test/test-custom-9 --size 9 --gpu 3 -f

# CUDA_VISIBLE_DEVICES=1,2,3 /goattack/scripts/attack.sh --komi 7.5 -t 1 -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 \
#     -n 10 -e test/test-raw-9 --size 9 --gpu 3 -f