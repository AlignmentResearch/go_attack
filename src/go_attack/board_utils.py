"""Math functions for manipulating Go vertices."""
import re
from typing import IO

import numpy as np

from go_attack.go import Move


def l1_distance(move1: Move, move2: Move) -> int:
    """Compute the L1 distance between two Go moves.

    Args:
        move1: A move
        move2: Another move

    Returns:
        The L1 distance between the two moves on the board.
    """
    (x1, y1), (x2, y2) = move1, move2
    return abs(x1 - x2) + abs(y1 - y2)


def mirror_move(move: Move, board_size: int = 19) -> Move:
    """Compute the 'Mirror Go' response to a move.

    We reflect the move about the y = x diagonal, unless the move is on the
    y = x diagonal, in which case we reflect about the y = -x diagonal.

    Args:
        move: A Go move
        board_size: The size of the board (default 19)

    Returns:
        The Mirror Go move.
    """
    last = board_size - 1
    opponent_x, opponent_y = move

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

    return Move(mirror_x, mirror_y)


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
        if msg == array_name:
            skip = False
        elif not skip:
            hit = numeric_regex.fullmatch(msg)
            if hit:
                row = [float(x.strip()) for x in hit[0].split()]
                array.append(row)
            else:
                break

    return np.array(array)
