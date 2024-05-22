"""Unit tests for the `go` module."""

from typing import Dict, Sequence

import numpy as np
import pytest

from ANONYMOUS_REPO.go import Game, Move


def create_game(
    board_size: int,
    board_states: Sequence[Sequence[Sequence[int]]],
) -> Game:
    """Test helper that creates a `Game` with the specified `board_states`."""
    game = Game(board_size=board_size)
    game.board_states.clear()
    game.board_states.extend(np.array(board) for board in board_states)
    # Populate `game.moves` with dummy moves so that functions that check the
    # length of `game.moves` work.
    game.moves.extend(Move(x=0, y=0) for _ in board_states[:-1])
    return game


@pytest.mark.parametrize(
    "game_kwargs",
    [
        {
            "board_size": 19,
            "komi": 0.0,
        },
        {
            "board_size": 5,
            "komi": -50.0,
        },
    ],
)
def test_sgf_convert_arguments(game_kwargs: Dict):
    """Checks `Game` SGF conversion parses `Game()` arguments correctly."""
    game = Game(**game_kwargs)
    parsed_game = Game.from_sgf(game.to_sgf())
    assert parsed_game.board_size == game.board_size
    assert parsed_game.komi == game.komi


def test_is_suicide():
    """Checks `Game.is_suicide` correctly detects suicide moves."""
    game = create_game(
        board_size=3,
        board_states=[
            [
                [2, 0, 0],
                [0, 2, 2],
                [2, 0, 1],
            ],
            [
                [2, 0, 0],
                [0, 2, 2],
                [2, 0, 1],
            ],
            [
                [2, 0, 0],
                [0, 2, 2],
                [2, 1, 0],
            ],
        ],
    )

    # Black taking a square surrounded by white is suicide.
    assert game.is_suicide(Move(x=0, y=1), turn_idx=0)
    # Black takes a square that creates a black group with no liberties is suicide.
    assert game.is_suicide(Move(x=1, y=0), turn_idx=0)

    # White taking a square surrounded by white is not suicide.
    assert not game.is_suicide(Move(x=0, y=1), turn_idx=1)

    # Black taking a square surrounded by white is not suicide if taking the
    # square surrounds a white group and creates a liberty.
    assert not game.is_suicide(Move(x=0, y=1), turn_idx=2)
