"""A basic implementation of Go with Tromp-Taylor rules."""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, List, NamedTuple, Optional, Tuple, Union

import numpy as np
from scipy.ndimage import distance_transform_cdt, label


class Color(Enum):
    """The color of a stone or vertex."""

    EMPTY = 0
    BLACK = 1
    WHITE = 2

    @classmethod
    def from_str(cls, s: str) -> "Color":
        """Parse a color from a string."""
        if s == "B":
            return Color.BLACK
        elif s == "W":
            return Color.WHITE
        else:
            raise ValueError(f"Invalid color string: {s}")

    def opponent(self):
        """Return the opponent of this color."""
        if self == Color.EMPTY:
            raise ValueError("Cannot get opponent of empty color")

        return Color.BLACK if self == Color.WHITE else Color.WHITE

    def __str__(self) -> str:
        """Return a string representation of this color ('B' or 'W')."""
        if self == Color.EMPTY:
            raise ValueError("The empty color has no string representation")

        return "B" if self == Color.BLACK else "W"


class IllegalMoveError(Exception):
    """Raised when an illegal move is made."""


# Alphabet without I
GO_LETTERS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"


def cartesian_to_numpy(x: int, y: int) -> Tuple[int, int]:
    """Convert Cartesian coordinates to NumPy coordinates or vice versa.

    Args:
        x: The x-coordinate.
        y: The y-coordinate.

    Returns:
        The coordinates in the opposite format.
    """
    # Transpose (x, y) <-> (row, col). We also need to flip the sign of the
    # y coordinate since NumPy places the origin at the top-left. Using
    # negative indices allows us to avoid asking the user for the board size.
    return -1 - y, x


# Involution
numpy_to_cartesian = cartesian_to_numpy


class Move(NamedTuple):
    """A move on the Go board, in zero-indexed Cartesian coordinates."""

    x: int
    y: int

    @classmethod
    def from_str(cls, s: str) -> Optional["Move"]:
        """Parse a move from a string like 'A5' or 'B7' or 'pass'."""
        if s == "pass":
            return None
        else:
            letter, num = s[0], int(s[1:])
            return Move(x=GO_LETTERS.find(letter), y=num - 1)

    def __str__(self):
        """Return the string representation of this move."""
        return f"{GO_LETTERS[self.x]}{self.y + 1}"


@dataclass(frozen=True)
class Game:
    """Encapsulates the state of a Go game.

    Since `Game` is a frozen dataclass you can't assign to its attributes,
    but no exception will be raised if you try to mutate `board_states`
    or `moves` in-place. Mutation may leave the board in an inconsistent
    state, so this is not recommended.

    Board states are represented as NumPy arrays so that, when you print
    a board state, the pieces are arranged visually the way you expect.
    """

    board_size: int
    board_states: List[np.ndarray] = field(default_factory=list)
    moves: List[Optional[Move]] = field(default_factory=list)
    komi: float = 7.5

    def __len__(self) -> int:
        """Return the number of turns in this game."""
        return len(self.moves)

    def __post_init__(self):
        """Initialize the history of board states."""
        # The board starts out empty
        board = np.zeros((self.board_size, self.board_size), dtype=np.uint8)
        self.board_states.append(board)

    def __repr__(self) -> str:
        """Return a string representation of this game."""
        # Omit the board state history since it can get very large
        board = self.board_states[-1]
        return f"Game(board_size={self.board_size}, komi={self.komi}, board={board})"

    def current_player(self, *, turn_idx: Optional[int] = None) -> Color:
        """Return the color of the current player."""
        return Color.BLACK if len(self.moves[:turn_idx]) % 2 == 0 else Color.WHITE

    def get_color(self, x: int, y: int, *, turn_idx: Optional[int] = None) -> Color:
        """Return the color of the point at (x, y) in the given turn."""
        board = self.board_states[turn_idx if turn_idx is not None else -1]

        # Transpose from (x, y) to (row, col) for NumPy, then flip the
        # row coordinate s.t. the *bottom* row is row 0.
        return Color(board[cartesian_to_numpy(x, y)])

    def skip_turn(self):
        """Skip the current turn (i.e. pass)."""
        self.board_states.append(self.board_states[-1])
        self.moves.append(None)

    def undo(self) -> np.ndarray:
        """Undo the last turn, returning the undone board."""
        self.moves.pop()
        return self.board_states.pop()

    def is_legal(self, move: Move, *, turn_idx: Optional[int] = None):
        """Return `True` iff `move` is legal at `turn_idx`."""
        # Rule 7. A move consists of coloring an *empty* point one's own color...
        if self.get_color(*move, turn_idx=turn_idx) != Color.EMPTY:
            return False

        # Rule 6. A turn is either a pass; or a move that *doesn't repeat* an
        # earlier grid coloring.
        next_board = self.virtual_move(*move, turn_idx=turn_idx)
        return not self.is_repetition(next_board)

    def is_over(self) -> bool:
        """Return `True` iff there have been two consecutive passes."""
        return len(self.moves) >= 2 and self.moves[-2:] == [None, None]

    def is_repetition(
        self,
        board: np.ndarray,
        *,
        turn_idx: Optional[int] = None,
    ) -> bool:
        """Return `True` iff `board` repeats an earlier board state."""
        # Sort of silly thing we have to do because of Python slicing semantics
        history = self.board_states[:turn_idx]
        return any(np.all(board == earlier) for earlier in history)

    def legal_move_mask(self, *, turn_idx: Optional[int] = None) -> np.ndarray:
        """Return a mask of all legal moves for the current player."""
        board = np.zeros((self.board_size, self.board_size), dtype=np.uint8)
        for x, y in self.legal_moves(turn_idx=turn_idx):
            board[cartesian_to_numpy(x, y)] = 1

        return board

    def legal_moves(self, *, turn_idx: Optional[int] = None) -> Iterable[Move]:
        """Return a generator over all legal moves for the current player."""
        for x in range(self.board_size):
            for y in range(self.board_size):
                if self.is_legal(Move(x, y), turn_idx=turn_idx):
                    yield Move(x, y)

    def move(self, x: int, y: int, *, check_legal: bool = True) -> None:
        """Make a move at (`x`, `y`)."""
        next_board = self.virtual_move(x, y)

        if check_legal:
            # Rule 7. A move consists of coloring an *empty* point one's own color...
            if self.get_color(x, y) != Color.EMPTY:
                raise IllegalMoveError("Cannot place stone on top of an existing stone")

            # Rule 6. A turn is either a pass; or a move that *doesn't repeat* an
            # earlier grid coloring.
            if self.is_repetition(next_board):
                raise IllegalMoveError(
                    "Superko violation: Cannot repeat an earlier board state",
                )

        self.board_states.append(next_board)
        self.moves.append(Move(x, y))

    def play_move(self, move: Optional[Move], *, check_legal: bool = True) -> None:
        """Pass if `move is None`, otherwise play the specified `Move` object."""
        if move is None:
            self.skip_turn()
        else:
            self.move(move.x, move.y, check_legal=check_legal)

    def virtual_move(
        self,
        x: int,
        y: int,
        *,
        turn_idx: Optional[int] = None,
    ) -> np.ndarray:
        """Compute what the board would look like if this move were made.

        Args:
            x: The x-coordinate of the move (zero-indexed).
            y: The y-coordinate of the move (zero-indexed).
            turn_idx: The index of the board state to use. Defaults to the
                most recent board state.

        Returns:
            A copy of the board state at `turn_idx` with the move applied.

        Raises:
            IllegalMoveError: Only if the move is out of bounds; other types
                of illegality are ignored by this method.
        """
        if not (x >= 0 and x < self.board_size):
            raise IllegalMoveError("X coordinate out of bounds")
        if not (y >= 0 and y < self.board_size):
            raise IllegalMoveError("Y coordinate out of bounds")

        board = self.board_states[turn_idx if turn_idx is not None else -1].copy()
        color = self.current_player()

        # Rule 7. A move consists of coloring an empty point one's own color...
        board[cartesian_to_numpy(x, y)] = color.value

        # ...then clearing the opponent color,
        self._clear_color(board, color.opponent())

        # ...and then clearing one's own color.
        self._clear_color(board, color)
        return board

    def score(self, turn_idx: Optional[int] = None) -> Tuple[int, int]:
        """Return the current score of the game as a (black, white) tuple."""
        board = self.board_states[turn_idx if turn_idx is not None else -1]

        # Distance of each point to the nearest black point.
        black_dists = distance_transform_cdt(
            board != Color.BLACK.value,
            metric="taxicab",
        )
        # Distance of each point to the nearest white point.
        white_dists = distance_transform_cdt(
            board != Color.WHITE.value,
            metric="taxicab",
        )
        # `territories` are labeled with integers from `1` to `num_trajectories`, with
        # contiguous groups of empty cells with the same label
        territories, num_territories = label(board == Color.EMPTY.value)

        # Rule 9. A player’s score is the number of points of her color...
        black_score = np.sum(board == Color.BLACK.value)
        white_score = np.sum(board == Color.WHITE.value) + self.komi

        # ...plus the number of empty points that only reach her color.
        for terr_idx in range(1, num_territories + 1):
            # A territory "reaches" a color iff any of its stones are 1 away
            # from a stone of that color
            terr_mask = territories == terr_idx
            terr_black_dists = black_dists * terr_mask
            terr_white_dists = white_dists * terr_mask
            reaches_black = np.any(terr_black_dists == 1)
            reaches_white = np.any(terr_white_dists == 1)

            if reaches_black and not reaches_white:
                black_score += terr_mask.sum()
            elif reaches_white and not reaches_black:
                white_score += terr_mask.sum()

        return black_score, white_score

    def winner(self) -> Optional[Color]:
        """Return the winner of the game, or `None` if the game is not over."""
        if not self.is_over():
            return None

        black_score, white_score = self.score()
        if black_score > white_score:
            return Color.BLACK
        elif white_score > black_score:
            return Color.WHITE
        else:
            return None

    @staticmethod
    def _clear_color(board: np.ndarray, color: Color):
        """Clear all stones of a given color."""
        # Rule 4. Clearing a color is the process of emptying all points of
        # that color that don’t reach empty.
        # `dists` is the distance of each point to the nearest empty point.
        dists = distance_transform_cdt(
            board != Color.EMPTY.value,
            metric="taxicab",
        )
        groups, num_groups = label(board == color.value)  # Find groups

        for group_idx in range(1, num_groups + 1):
            # Group reaches empty iff any of its stones are 1 away from empty
            group_mask = groups == group_idx
            group_dists = dists * group_mask
            reaches_empty = np.any(group_dists == 1)

            if not reaches_empty:
                board[group_mask] = Color.EMPTY.value

        return board

    @classmethod
    def from_sgf(cls, sgf_string: Union[Path, str], check_legal: bool = True) -> "Game":
        """Create a `Board` from an SGF string."""
        sgf_string = str(sgf_string).strip()

        # Try to detect the board size from the SGF string using the SZ[]
        # property; if that fails, use the default board size of 19.
        maybe_size = re.search(r"SZ\[([0-9]+)\]", sgf_string)
        game = cls(int(maybe_size.group(1)) if maybe_size else 19)

        turn_regex = re.compile(r"(B|W)\[([a-z]{0,2})\]")
        for i, hit in enumerate(turn_regex.finditer(sgf_string)):
            expected_player = Color.BLACK if i % 2 == 0 else Color.WHITE
            player = Color.from_str(hit.group(1))

            if player != expected_player:
                p1, p2 = str(expected_player), str(player)
                raise ValueError(f"Expected {p1} to play on turn {i + 1}, got {p2}")

            vertex = hit.group(2)
            if not vertex:
                move = None
            else:
                x, y = ord(vertex[0]) - ord("a"), ord(vertex[1]) - ord("a")
                move = Move(x, y)

            game.play_move(move, check_legal=check_legal)

        return game

    def to_sgf(self, comment: str = "") -> str:
        """Return an SGF string representing the game."""
        # We say we're using "New Zealand" rules in the SGF
        header = f"(;FF[4]SZ[{self.board_size}]RU[NZ]"
        if comment:
            header += f"C[{comment}]"

        ascii_a = ord("a")
        sgf_moves = []

        for i, move in enumerate(self.moves):
            player = "B" if i % 2 == 0 else "W"
            if move is None:
                sgf_moves.append(f"{player}[]")
            else:
                x = chr(ascii_a + move.x)
                y = chr(ascii_a + move.y)

                sgf_moves.append(f"{player}[{x}{y}]")

        body = ";".join(sgf_moves)
        return f"{header}\n;{body})"
