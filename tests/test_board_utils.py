from go_attack.board_utils import mirror_move
from itertools import product
import pytest
import sente


@pytest.mark.parametrize("board_size", [9, 13, 19])
def test_mirror_move(board_size: int):
    stones = (sente.stone.BLACK, sente.stone.WHITE)
    for x, y, stone in product(range(board_size), range(board_size), stones):
        move = sente.Move(x, y, stone)
        mirrored = mirror_move(move, board_size)
        mirrored2 = mirror_move(mirrored, board_size)

        # The mirrored move should stay inside the board
        assert 0 <= mirrored.get_x() < board_size
        assert 0 <= mirrored.get_y() < board_size

        # This is an https://en.wikipedia.org/wiki/Involution_(mathematics);
        # mirroring a move twice should return the original move
        assert move.get_x() == mirrored2.get_x()
        assert move.get_y() == mirrored2.get_y()
        assert move.get_stone() == mirrored2.get_stone()
