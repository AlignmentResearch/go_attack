"""Math functions for manipulating Go vertices."""
import re
from typing import IO

import numpy as np
import sente


def l1_distance(move1: sente.Move, move2: sente.Move) -> int:
    """Compute the L1 distance between two Sente moves.

    Args:
        move1: A Sente move
        move2: Another Sente move

    Returns:
        The L1 distance between the two moves on the board.
    """
    x1, y1 = move1.get_x(), move1.get_y()
    x2, y2 = move2.get_x(), move2.get_y()
    return abs(x1 - x2) + abs(y1 - y2)


def mirror_move(move: sente.Move, board_size: int = 19) -> sente.Move:
    """Compute the 'Mirror Go' response to a move.

    We reflect the move about the y = x diagonal, unless the move is on the
    y = x diagonal, in which case we reflect about the y = -x diagonal.

    Args:
        move: A Sente move
        board_size: The size of the board (default 19)

    Returns:
        The Mirror Go move.
    """
    last = board_size - 1
    opponent_x, opponent_y = move.get_x(), move.get_y()

    black = move.get_stone() == sente.stone.BLACK
    stone = sente.stone.WHITE if black else sente.stone.BLACK

    # The "move" is out of bounds, so we can't mirror it.
    # Sente appears to use OOB moves to indicate pass.
    if opponent_x > last or opponent_y > last:
        return sente.Move(opponent_x, opponent_y, stone)

    # Did they play on the y = x diagonal?
    # If so, mirror across the y = -x diagonal.
    if opponent_x == last - opponent_y:
        # Mirror across the y = -x diagonal
        mirror_x = opponent_y
        mirror_y = opponent_x

    # Normal case: mirror across the y = x diagonal
    else:
        mirror_x = last - opponent_x
        mirror_y = last - opponent_y

    return sente.Move(mirror_x, mirror_y, stone)


def parse_array(gtp_stream: IO[bytes], array_name: str, size: int) -> np.ndarray:
    """Parse an array from a GTP stream.

    Args:
        gtp_stream: A GTP stream from KataGo, which is assumed to have just
            received the command `kata-raw-nn`.
        array_name: The header indicating the array to parse. Examples
            include `policy` and `whiteOwnership`.
        size: The size of the board.

    Returns:
        The array in NumPy format.
    """
    array = []
    numeric_regex = re.compile(rf"((-?[0-9.]+|NAN)\s*){{{size}}}")
    skip = True
    while True:
        msg = gtp_stream.readline().decode("ascii").strip()
        # print(msg)
        if msg == array_name:
            skip = False
        elif not skip:
            hit = numeric_regex.fullmatch(msg)
            if hit:
                row = [float(x.strip()) for x in hit[0].split()]
                array.append(row)
            else:
                break

    return np.flip(array, axis=0)
