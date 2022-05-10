import os 

for i in range(333, 430):
    string = "/goattack/engines/KataGo-custom/cpp/katago evalsgflong -config /goattack/configs/katago/gtp_custom.cfg "
    string += f"-model /goattack/models/g170-b40c256x2-s5095420928-d1229425124.bin.gz -m {i} -log-raw-nn "
    # string += "/goattack/sgf4test/w1600b_atk1600-gt-19x19_game-0.sgf"
    string += "/goattack/sgf4test/hand_designed.sgf"

    for _ in range(10):
        os.system(string)