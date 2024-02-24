"""Unit tests for the `board_utils` module."""

from itertools import product

import pytest

from go_attack.board_utils import mirror_move
from go_attack.go import Move


@pytest.mark.parametrize("board_size", [9, 13, 19])
def test_mirror_move(board_size: int):
    """Make sure `mirror_move` is an involution."""
    for x, y in product(range(board_size), range(board_size)):
        move = Move(x, y)
        mirrored = mirror_move(move, board_size)
        mirrored2 = mirror_move(mirrored, board_size)

        # The mirrored move should stay inside the board
        assert 0 <= mirrored.x < board_size
        assert 0 <= mirrored.y < board_size

        # This is an https://en.wikipedia.org/wiki/Involution_(mathematics);
        # mirroring a move twice should return the original move
        assert move.x == mirrored2.x
        assert move.y == mirrored2.y
