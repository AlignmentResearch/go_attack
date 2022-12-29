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
* Games are all on 19x19 boards.
* Assuming the victim does not have a visit count near 600, we guess at whether
  the adversary of victim is playing by looking at the number of root visits.
* A finished game is indicated by a line containing "Finished game". We assume
  that this indicates the game that had the latest move printed finished. This
  is probably not true in general due to interleaving output issues, but it
  might work if moves tend to have large time gaps in between each other and
  there are few parallel games.
* This script has only been tested on a file where all games end with
  resignation.
"""

import argparse
import pathlib
import re
from dataclasses import dataclass
from typing import Callable, Iterable, List, Literal, Optional, Sequence, TypeVar

import numpy as np

import go_attack.go as go

ADVERSARY_VISITS = 600
BOARD_SIZE = 19
T = TypeVar("T")


@dataclass
class BoardInfo:
    """Info parsed from a board state string."""

    # The current board.
    board: np.ndarray
    # Which move it is.
    move_num: int
    # The past <= 3 moves, with move_history[-1] being the most recent.
    move_history: List[Optional[go.Move]]
    # The next move, to be played on move `move_num + 1`.
    proposed_move: Optional[go.Move]
    # Which bot moved first in this game.
    black_player: Literal["adv", "victim"]
    # True if the game is over.
    is_finished: bool


@dataclass
class GameAndBoardInfo:
    """Game and its latest BoardInfo."""

    game: go.Game
    board: BoardInfo


def split_iterator(
    predicate: Callable[[T], bool],
    it: Iterable[T],
) -> Iterable[Iterable[T]]:
    """Partitions an iterable according to a predicate.

    Partitions an iterable into several iterables, splitting before each element
    satisfying the predicate.

    E.g.,
        list(split_iterator(range(5), lambda n: n % 2 == 0))
        == [[0, 1], [2, 3], [4]]
    """
    chunk = []
    for x in it:
        if predicate(x) and len(chunk) > 0:
            yield chunk
            chunk = []
        chunk.append(x)
    if len(chunk) > 0:
        yield chunk


def parse_board_info(board_str: Sequence[str]) -> BoardInfo:
    """Parses board state string into BoardInfo."""
    """
    A typical board state string:
2022-12-24 22:22:30+0000: MoveNum: 339 HASH: 86620817F6D87517F90F73814E5065D5
   A B C D E F G H J K L M N O P Q R S T
19 O . O O X X X X X X X X X X X . X X X
18 O O . O O O O O O O O O O O X X X O X
17 X O O X X X X X X X X X X X X X O O O
16 X O X X . . . . . X . X . . . . X O .
15 X O X . X . . . . X . . . . . X X O X3
14 X X X . . X X O O X . X O . . . X O .
13 . X . . . O O X O X O . O . . . X O .
12 . X1X X . O X X O O O O O O . . X O O
11 . O O O O O O X X O O X X O . . X O X
10 . . O X O X O O X O X X O . O . X O X
 9 . . O X X X X X X X X X X O O . X O X
 8 . O O X O O O O X O O X O X X X X O X
 7 X O X X O . . O X O O O O O . . X O X
 6 . X X X O X . O X O X O . X . . X O X
 5 X X . X O . O O X O X O . . . . X O X
 4 . X @ X O O X X X X X O . X . X X O X
 3 O O O X X X X O O O O O . . X X X O X
 2 X X O2. X O O O X . O X X . X O O O X
 1 O . . X X X O . X O . . . . X X X X X


Rules: koPOSITIONALscoreAREAtaxNONEsui1komi6.5
Root visits: 600
Policy surprise 1.13525
Raw WL 0.612673
PV: C4 T14 C1 T13 D2 T16 C5 pass A8 pass A6 O10
Tree:
: T  51.84c W  56.31c S  -1.73c (+40.6 L -142.5) N     600  --  C4 T14 C1 T13 D2 T16 C5
---White(^)---
C4  : T  57.23c W  61.00c S  -1.56c (+42.0 L -141.7) LCB   47.08c P  7.27% WF  97.5 PSV     109 N     312  --  C4 T14 C1 T13 D2 T16 C5 pass
A8  : T  57.40c W  60.10c S  -0.42c (+47.8 L -148.0) LCB   46.77c P  2.61% WF  39.8 PSV      38 N      91  --  A8 T14 C4 F7 B1 T16 T13 T15
T14 : T  35.63c W  39.35c S  -1.96c (+37.4 L -134.7) LCB   -4.29c P 56.05% WF  31.9 PSV      33 N      83  --  T14 C1 B1 A2 B2 F7 C4 D2
D2  : T  49.06c W  56.39c S  -1.00c (+44.5 L -144.6) LCB   11.23c P  7.48% WF  12.0 PSV      11 N      34  --  D2 T14 C4 T13 T16 T14 C1 T13
C1  : T  47.38c W  58.69c S  -2.83c (+35.7 L -144.8) LCB   -0.53c P  8.21% WF  10.1 PSV      10 N      37  --  C1 T14 C4 T13 D2 T16 C5 P7
A4  : T  44.52c W  52.68c S  -5.04c (+20.2 L -147.8) LCB  -10.80c P  3.29% WF  12.5 PSV       3 N      36  --  A4 T14 C4 T16 T13 T15 C1 G6
B1  : T  13.72c W  28.48c S  -9.66c ( -8.4 L -149.1) LCB -3356.75c P  7.87% WF   1.8 PSV       2 N       6  --  B1 T14 C1 C4
    """
    move_num = int(re.search(r"MoveNum: (\d+)", board_str[0]).groups(1)[0])
    visits = int(re.search(r"Root visits: (\d+)", board_str[24]).groups(1)[0])
    black_player = (
        "adv"
        if (move_num % 2 == 0) == (abs(visits - ADVERSARY_VISITS) <= 1)
        else "victim"
    )
    is_finished = any("Finished" in line for line in board_str)

    board = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.uint8)
    move_history = [None for _ in range(min(3, move_num))]
    proposed_move = None
    for y in range(BOARD_SIZE):
        line = board_str[20 - y]
        for x in range(BOARD_SIZE):
            square = line[3 + 2 * x]
            if square == "X":
                board[go.cartesian_to_numpy(x, y)] = go.Color.BLACK.value
            elif square == "O":
                board[go.cartesian_to_numpy(x, y)] = go.Color.WHITE.value
            elif square == "@":
                proposed_move = go.Move(x, y)
            elif square != ".":
                raise ValueError(f"Unexpected square {square} in line: {line}")

            annotation_index = 4 + 2 * x
            if annotation_index < len(line):
                annotation = line[annotation_index]
                if annotation == "1":
                    move_history[0] = go.Move(x, y)
                elif annotation == "2":
                    move_history[1] = go.Move(x, y)
                elif annotation == "3":
                    move_history[2] = go.Move(x, y)
                elif annotation not in " \n":
                    raise ValueError(
                        f"Unexpected annotation {annotation} in line: {line}",
                    )

    return BoardInfo(
        board=board,
        move_num=move_num,
        move_history=move_history,
        proposed_move=proposed_move,
        black_player=black_player,
        is_finished=is_finished,
    )


def check_board_matches_game(
    game: go.Game,
    last_board: BoardInfo,
    next_board: BoardInfo,
):
    """Returns true if `next_board` is a valid next board for (game, last_board)."""
    if last_board.move_num + 1 != next_board.move_num:
        return False
    if last_board.black_player != next_board.black_player:
        return False
    if (last_board.move_history + [last_board.proposed_move])[
        -len(next_board.move_history) :
    ] != next_board.move_history:
        return False
    if last_board.proposed_move is None:
        if not np.array_equal(last_board.board, next_board.board):
            return False
    elif not np.array_equal(
        game.virtual_move(*last_board.proposed_move),
        next_board.board,
    ):
        return False
    return True


def main() -> None:
    """Entrypoint for script."""
    parser = argparse.ArgumentParser(
        description="Constructs a SGF matching the board state history.",
    )
    parser.add_argument(
        "input_file",
        type=pathlib.Path,
        help="Path to input file of board states.",
    )
    parser.add_argument(
        "output_dir",
        type=pathlib.Path,
        help="Path to the directory at which to output SGFs.",
    )
    args = parser.parse_args()

    unfinished_games: List[GameAndBoardInfo] = []
    num_finished_games = 0
    with open(args.input_file, "r") as f:
        is_board_state_start = lambda l: "MoveNum" in l
        for i, board_str in enumerate(split_iterator(is_board_state_start, f)):
            if i == 0:
                # The first result is initialization output, not a board.
                continue
            if i % 100 == 0:
                print(f"Parsing board state {i}...")
            board = parse_board_info(board_str)

            unfinished_game_index = None
            for j, game in enumerate(unfinished_games):
                if check_board_matches_game(game.game, game.board, board):
                    unfinished_game_index = j
                    break
            if unfinished_game_index is None:
                assert board.move_num == 0
                unfinished_games.append(GameAndBoardInfo(go.Game(BOARD_SIZE), board))
            elif board.is_finished:
                unfinished_games.pop(j)
            else:
                unfinished_games[j].game.play_move(board.move_history[-1])
                unfinished_games[j].board = board

    total_num_games = len(unfinished_games) + num_finished_games
    print(f"Unfinished games: {len(unfinished_games)}/{total_num_games}")

    args.output_dir.mkdir(exist_ok=True, parents=True)
    for i, (game, board) in enumerate(unfinished_games):
        with open(args.output_dir / f"game{i}.sgf", "w"):
            f.write(game.to_sgf(black_name=board.black_player))


if __name__ == "__main__":
    main()
