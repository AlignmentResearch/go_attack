# python3 sgf2json.py -s ../openings/motivation.sgf -v 500 -j ../openings_json/motivation_500.json
# python3 sgf2json.py -s ../openings/motivation.sgf -v 5000 -j ../openings_json/motivation_5000.json

# python3 sgf2json.py -s ../4analysis/game-1.sgf -v 1 -j ../openings_json/game_1.json
# python3 sgf2json.py -s ../4analysis/game-1.sgf -v 1600 -j ../openings_json/game_1600.json
# python3 sgf2json.py -s ../4analysis/game-1.sgf -v 6400 -j ../openings_json/game_6400.json
# python3 sgf2json.py -s ../4analysis/game-1.sgf -v 64000 -j ../openings_json/game_64000.json
# python3 sgf2json.py -s ../4analysis/game-1.sgf -v 640000 -j ../openings_json/game_640000.json


import re
import json

def convert_single(item):
    item = re.search(r"([BW])\[([a-s]{0,2})\]",item)
    if item is not None:
        color, coor = item.groups()
        if len(coor) != 2:
            return None
        coor = coor.upper()
        char = coor[0]
        if coor[0] >= "I":
            char = chr(ord(coor[0]) + 1)
        num = ord("S") - ord(coor[1]) + 1
        coor = char + str(num)
        return [color, coor]
    else:
        return None

def main(args):
    with open(args.sgfpath, "r") as file:
        line = file.read()
    
    # aim = re.search(r"PL\[[BW]\];(.*)PL\[[BW]\]",line)
    # aim = aim.group(1)

    aim1 = re.sub("\n", "", line)
    # aim = re.search(r"PL\[[BW]\];(.*)B\[\];W\[\]",line)
    aim2 = aim1[712:-1]
    # print(aim2)
    aim3 = re.sub("PL\[W\];", "", aim2)
    aim4 = re.sub(";W\[\]", "", aim3)
    aim5 = re.sub(";B\[\]", "", aim4)
        
    moves = list(map(convert_single, aim5.split(";")))

    dict4json = {
        "id":"motivation",
        "initialStones":[],
        "moves":moves[:356],
        "maxVisits":int(args.visits),
        "rules":"tromp-taylor",
        "komi":7.5,
        "boardXSize":19,
        "boardYSize":19,
        # "analyzeTurns":list(range(0, len(moves)+1)[333:])
        "analyzeTurns":[355]
    }

    # dict4json
    line = json.dumps(dict4json)
    line = "".join(line.split(" "))
    print(repr(line))
    if args.jsonpath:
        with open(args.jsonpath, 'w') as file:
            file.write(line)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--sgfpath", type=str, default="../games/b40vb40-n50-o-w1600b1600/game-1.sgf")
    parser.add_argument("-v", "--visits", type=str, default=500)
    parser.add_argument("-j", "--jsonpath", type=str, default=None)
    args = parser.parse_args()
    
    main(args)