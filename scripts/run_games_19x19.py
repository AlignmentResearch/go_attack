import os

GPUs = [0]
GPUstrs = ' '.join(list(map(str, GPUs)))

# # Baselines
# python /goattack/scripts/attack.py -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 \
#     --komi 7.5 --size 19 --n 50 -e baseline/komi7.0-w1600b1600-9x9 --gpu 3


# # Attack Expansion Only
# script = "python /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 "
# script += f"--komi 7.5 --size 19 -sa 99999 -sb 0 -ae -n 20 -e atkexpand/w1600b_atk1600-atkexpand-9x9 "
# script += f"--gpu {GPUstrs}"
# os.system(script)


# Soft Attack
# [50, 100, 200, 400, 800, 1200, 1600]

# for sa in [50, 100, 200, 400, 800, 1200, 1600]:
#     script = "python /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 "
#     script += f"--komi 7.5 --size 19 -sa {sa} -sb 0 -n 20 -e softatk/sa{sa}-w1600b_atk1600-9x9 "
#     script += f"--gpu {GPUstrs}"
#     os.system(script)

# # Soft Attack + Attack Expansion
# # [0, 50, 100, 200, 400, 800, 1200, 1600]

# for sa in [0, 50, 100, 200, 400, 800, 1200, 1600]:
#     script = "python /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 "
#     script += f"--komi 7.5 --size 19 -sa {sa} -sb 0 -ae -n 20 -e softatk_atkexpand/sa{sa}-w1600b_atk1600-atkexpand-9x9 "
#     script += f"--gpu {GPUstrs}"
#     os.system(script)

# Soft Attack + Soft Expansion
# [50, 100, 200, 400]

for se in [50, 100, 200, 400]:
    script = "python /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 "
    script += f"--komi 7.5 --size 19 -sa 800 -sb 0 -se {se} -ae -n 20 -e softatk_softexpand/sa800-se{se}-w1600b_atk1600-atkexpand-9x9 "
    script += f"--gpu {GPUstrs}"
    os.system(script)

# # MCTS soft backup
# # [50, 100, 200, 400, 800, 1200, 1600]

# for sb in [50, 100, 200, 400, 800, 1200, 1600]:
#     script = "python /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 "
#     script += f"--komi 7.5 --size 19 -sa 0 -sb {sb} -n 20 -e mctssb/mctssb{sb}-w1600b_atk1600-9x9 "
#     script += f"--gpu {GPUstrs}"
#     os.system(script)


# # Minimax soft backup
# # [50, 100, 200, 400, 800, 1200, 1600]

# for sb in [50, 100, 200, 400, 800, 1200, 1600]:
#     script = "python /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 "
#     script += f"--komi 7.5 --size 19 -sa 0 -sb {sb} -ms -n 20 -e minimaxsb/minimaxsb{sb}-w1600b_atk1600-9x9 "
#     script += f"--gpu {GPUstrs}"
#     os.system(script)


# # MCTS soft backup + Attack Expansion
# # [50, 100, 200, 400, 800, 1200, 1600]

# for sb in [50, 100, 200, 400, 800, 1200, 1600]:
#     script = "python /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 "
#     script += f"--komi 7.5 --size 19 -sa 0 -sb {sb} -ae -n 20 -e mctssb_atkexpand/mctssb{sb}-w1600b_atk1600-atkexpand-9x9 "
#     script += f"--gpu {GPUstrs}"
#     os.system(script)

# # Minimax soft backup + Attack Expansion
# # [50, 100, 200, 400, 800, 1200, 1600]

# for sb in [50, 100, 200, 400, 800, 1200, 1600]:
#     script = "python /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 "
#     script += f"--komi 7.5 --size 19 -sa 0 -sb {sb} -ms -ae -n 20 -e minimaxsb_atkexpand/minimaxsb{sb}-w1600b_atk1600-atkexpand-9x9 "
#     script += f"--gpu {GPUstrs}"
#     os.system(script)

# # Tests and Debug

# python /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 \
#     --komi 7.5 --size 19 -sa 0 -sb 0 -se 25 -ae -n 20 -e test/test-soft-expand --gpu 0

# python /goattack/scripts/attack.py -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 \
#     --komi 7.5 --size 19 --n 20 -e test/test-raw-9 --gpu 3