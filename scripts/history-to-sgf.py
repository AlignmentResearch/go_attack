"""Parses a match log and prints out SGFs for all unfinished games.

Developer notes on parsing match log:
* The '@' symbol is where the current bot is planning on placing its next move
  (at the move number right after MoveNum). However, the bot may resign instead
  of placing the move. No symbol is displayed if the current bot is planning on
  passing.
* The numbers '1', '2', '3' are displayed to the right of the most recent 3
  moves, with '3' being next to the most recent move assuming there have been at
  least three moves. If MoveNum < 3, then MoveNum is displayed to the right of
  the most recent move. If a number is missing, then that move was a pass.

Assumptions:
* Assuming the victim does not have a visit count near 600, we guess at whether
  the adversary of victim is playing by looking at the number of root visits.
* A finished game is indicated by a line containing "Finished game". We assume
  that this indicates the game that had the latest move printed finished. This
  is probably not true in general due to interleaving output issues, but it
  might work if moves tend to have large time gaps in between each other and
  there are few parallel games.
"""

import argparse
import pathlib
from dataclasses import dataclass
from typing import Sequence

import sgfmill.sgf

from go_attack.go import Move

LINES_PER_BOARD_STATE = 21
# Expected number of characters in each
BOARD_ROW_STR_LEN = 40

@dataclass
class BoardInfo:
    """Info about a board state."""
    # List of latest moves in ascending move order.
    move_history: List[Move]
    # Current move number, before the last move in move_history
    move_num: int

    board_state:

def parse_board_state(board: Sequence[str]) -> BoardInfo:
    """Parses board state string into BoardInfo."""
    assert len(board) == LINES_PER_BOARD_STATE

def main() -> None:
    """Entrypoint for script."""
    parser = argparse.ArgumentParser(
            description="Constructs a SGF matching the board state history."
    )
    parser.add_argument(
            "input_file",
            type=pathlib.Path,
            help="Path to input file of board states.",
    )
    args = parser.parse_args()

    with open(args.input_file, "r") as f:
        file_contents = [line.rstrip() for line in f]
    if len(file_contents) % LINES_PER_BOARD_STATES != 0:
        raise ValueError(
            "Expected number of lines to be divisible by "
            f"{LINES_PER_BOARD_STATES}, got {len(file_contents)}"
        )
    move_history = []



    print(file_contents)

if __name__ == "__main__":
    main()
