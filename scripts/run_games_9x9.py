from time import sleep
from copy import copy
from subprocess import Popen
from collections import deque

def addCmds(cmds):
    # # Baselines
    # cmds.append("python3 /goattack/scripts/attack.py -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 " + 
    #     "--komi 7 --size 9 -n 100 -e baseline/komi7.0-w1600b1600-9x9")
    
    # # Attack Expansion Only
    # cmds.append("python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 " +
    # "--komi 7 --size 9 -sa 99999 -sb 0 -ae -n 50 -e atkexpand/w1600b_atk1600-atkexpand-9x9")

    # # Soft Attack [50, 100, 200, 400, 800, 1200, 1600]

    # for sa in [50, 100, 200, 400, 800, 1200, 1600]:
    #     cmds.append("python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 " +
    #         f"--komi 7 --size 9 -sa {sa} -sb 0 -n 50 -e softatk/sa{sa}-w1600b_atk1600-9x9")

    # # Soft Attack + Attack Expansion [0, 50, 100, 200, 400, 800, 1200, 1600]

    # for sa in [0, 50, 100, 200, 400, 800, 1200, 1600]:
    #     cmds.append("python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 " + 
    #         f"--komi 7 --size 9 -sa {sa} -sb 0 -ae -n 50 -e softatk_atkexpand/sa{sa}-w1600b_atk1600-atkexpand-9x9")

    # # Soft Attack + Soft Expansion [50, 100, 200, 400]

    # for se in [50, 100, 200, 400]:
    #     cmds.append("python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 " +
    #         f"--komi 7 --size 9 -sa 800 -sb 0 -se {se} -ae -n 50 -e softatk_softexpand/sa800-se{se}-w1600b_atk1600-atkexpand-9x9")

    # # MCTS soft backup [50, 100, 200, 400, 800, 1200, 1600]

    # for sb in [50, 100, 200, 400, 800, 1200, 1600]:
    #     cmds.append("python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 " + 
    #         f"--komi 7 --size 9 -sa 0 -sb {sb} -n 50 -e mctssb/mctssb{sb}-w1600b_atk1600-9x9")


    # # Minimax soft backup [50, 100, 200, 400, 800, 1200, 1600]

    # for sb in [50, 100, 200, 400, 800, 1200, 1600]:
    #     cmds.append("python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 " + 
    #         f"--komi 7 --size 9 -sa 0 -sb {sb} -ms -n 50 -e minimaxsb/minimaxsb{sb}-w1600b_atk1600-9x9")


    # # MCTS soft backup + Attack Expansion [50, 100, 200, 400, 800, 1200, 1600]

    # for sb in [50, 100, 200, 400, 800, 1200, 1600]:
    #     cmds.append("python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 "
    #         f"--komi 7 --size 9 -sa 0 -sb {sb} -ae -n 50 -e mctssb_atkexpand/mctssb{sb}-w1600b_atk1600-atkexpand-9x9")

    # # Minimax soft backup + Attack Expansion
    # # [50, 100, 200, 400, 800, 1200, 1600]

    # for sb in [50, 100, 200, 400, 800, 1200, 1600]:
    #     cmds.append("python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 " + 
    #         f"--komi 7 --size 9 -sa 0 -sb {sb} -ms -ae -n 50 -e minimaxsb_atkexpand/minimaxsb{sb}-w1600b_atk1600-atkexpand-9x9")

    # Motivation Ground Truth

    for numPlayouts in [200, 1600]:
        # gt_visible
        cmds.append(f"python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp {numPlayouts} -wp {numPlayouts} -t 1 " +
            f"--komi 7 --size 9 -n 25 -e full-motiv-gt/w{numPlayouts}b_atk{numPlayouts}-gt-9x9 -gt -o -f")

        # cmds.append(f"python3 /goattack/scripts/attack.py -p white -b gtp_black.cfg -w gtp_white.cfg -bp {numPlayouts} -wp {numPlayouts} -t 1 " + 
        #     f"--komi 7 --size 9 -n 25 -e full-motiv-gt/w_atk{numPlayouts}b{numPlayouts}-gt-9x9 -gt -o")

        # gt_attack
        cmds.append(f"python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp {numPlayouts} -wp {numPlayouts} -t 1 " + 
            f"--komi 7 --size 9 -n 25 -sa 0 -e full-motiv-gt/sa0-w{numPlayouts}b_atk{numPlayouts}-gt-9x9 -gt -o -f")

        # cmds.append(f"python3 /goattack/scripts/attack.py -p white -b gtp_black.cfg -w gtp_white.cfg -bp {numPlayouts} -wp {numPlayouts} -t 1 " +
        #     f"--komi 7 --size 9 -n 25 -sa 0 -e full-motiv-gt/sa0-w_atk{numPlayouts}b{numPlayouts}-gt-9x9 -gt -o")

        # motiv_baseline
        cmds.append(f"python3 /goattack/scripts/attack.py -b gtp_black.cfg -w gtp_white.cfg -bp {numPlayouts} -wp {numPlayouts} -t 1 " + 
            f"--komi 7 --size 9 -n 25 -e motiv/w{numPlayouts}b{numPlayouts}-motiv-9x9 -o -f")

    for blackNumPlayouts in [1, 50, 100, 200, 400, 800, 1200]:
        cmds.append(f"python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp {blackNumPlayouts} -wp 1600 -t 1 " + 
            f"--komi 7 --size 9 -n 25 -e full-motiv-gt/w1600b_atk{blackNumPlayouts}-motiv-gt-9x9 -gt -o -f")

    # for blackNumPlayouts in [1, 100, 200, 400, 800, 1200]:
        # motiv_baseline
        cmds.append(f"python3 /goattack/scripts/attack.py -b gtp_black.cfg -w gtp_white.cfg -bp {blackNumPlayouts} -wp 1600 -t 1 " + 
            f"--komi 7 --size 9 -n 25 -e motiv/w1600b{blackNumPlayouts}-motiv-9x9 -o -f")

    # # Tests and Debug

    # cmds.append(f"python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 " + 
    #     f"--komi 7 --size 9 -sa 0 -sb 0 -se 25 -ae -n 50 -e test/test-soft-expand")

    # cmds.append(f"python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 50 -wp 50 -t 1 " +
    #     f"--komi 7 --size 9 -n 2 -e test/test-new-print --gpu 0")

    # cmds.append(f"python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1600 -wp 1600 -t 1 " +
    #     f"--komi 7 --size 9 -n 25 -sa 9999 -e full-motiv-gt/sa9999-w_atk100b100-9x9 -n 50 -gt -o -f")

    # cmds.append(f"python3 /goattack/scripts/attack.py -p black -b gtp_black.cfg -w gtp_white.cfg -bp 1 -wp 1600 -t 1 " + 
    #         f"--komi 7 --size 9 -n 1 -e test/w1600b_atk1-motiv-gt-9x9 -gt -o -f")

    return cmds

def main(cmds, gpus):
    processes = deque()
    while len(cmds) + len(processes) > 0:
        assert len(gpus) >= 0
        if len(gpus) > 0 and len(cmds) > 0:
            if len(cmds) == 1:
                gpu = " ".join([str(g) for g in gpus])
            else:
                gpu = gpus.popleft()
            cmd = cmds.popleft()
            cmd += f" --gpu {gpu}"
            print(f"[GPU {gpu}] Running {cmd} ...")
            process = Popen(cmd, shell=True)
            processes.append((gpu, process))
        else:
            for idx, p in enumerate(copy(processes)):
                returnValue = p[-1].poll()
                if returnValue is not None: 
                    gpus.append(p[0])
                    print(f"[GPU {p[0]}] Process finished (return value {returnValue}), released ...")
                    del processes[idx]
                    break   
                else:
                    sleep(60)

        # for cmd in cmds:
        #     processDict[] = Popen(cmd)

if __name__ == "__main__":
    cmds = deque([])
    gpus = deque([0, 1, 2])
    cmds = addCmds(cmds)
    main(cmds, gpus)
