"""A basic implementation of Go with Tromp-Taylor rules."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, NamedTuple, Optional, Tuple

import numpy as np
import re
from numpy.typing import NDArray
from scipy.ndimage import distance_transform_cdt, label


class Color(Enum):
    """The color of a stone."""

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
        assert self != Color.EMPTY
        return Color.BLACK if self == Color.WHITE else Color.WHITE

    def __str__(self) -> str:
        """Return a string representation of this color ('B' or 'W')."""
        assert self != Color.EMPTY
        return "B" if self == Color.BLACK else "W"


class IllegalMoveError(Exception):
    """Raised when an illegal move is made."""

    pass


# Alphabet without I
GO_LETTERS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"


class Move(NamedTuple):
    """A move on the Go board."""

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
    """Encapsulates the state of a Go game."""

    board_size: int
    board_states: List[NDArray[np.uint8]] = field(default_factory=list)
    moves: List[Optional[Move]] = field(default_factory=list)
    komi: float = 7.5

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

    def current_player(self) -> Color:
        """Return the color of the current player."""
        return Color.BLACK if len(self.moves) % 2 == 0 else Color.WHITE

    def get_color(self, x: int, y: int, *, turn_idx: int = -1) -> Color:
        """Return the color of the point at (x, y) in the given turn."""
        board = self.board_states[turn_idx]
        return Color(board[self.board_size - y - 1, x])

    def skip_turn(self):
        """Skip the current turn (i.e. pass)."""
        self.board_states.append(self.board_states[-1])
        self.moves.append(None)

    def undo(self) -> NDArray[np.uint8]:
        """Undo the last turn, returning the undone board."""
        self.moves.pop()
        return self.board_states.pop()

    def is_legal(self, move: Move, *, turn_idx: int = -1):
        """Return `True` iff `move` is legal at `turn_idx`."""
        # 7. A move consists of coloring an *empty* point one's own color...
        if self.get_color(*move, turn_idx=turn_idx) != Color.EMPTY:
            return False

        # 6. A turn is either a pass; or a move that *doesn't repeat* an
        # earlier grid coloring.
        next_board = self.virtual_move(*move)
        return not self.is_repetition(next_board)

    def is_over(self) -> bool:
        """Return `True` iff there have been two consecutive passes."""
        return len(self.moves) >= 2 and self.moves[-2:] == [None, None]

    def is_repetition(self, board: NDArray[np.uint8], *, turn_idx: int = -1) -> bool:
        """Return `True` iff `board` repeats an earlier board state."""
        # Sort of silly thing we have to do because of Python slicing semantics
        history = self.board_states[:turn_idx] if turn_idx != -1 else self.board_states
        return any(np.all(board == earlier) for earlier in history)

    def legal_move_mask(self, *, turn_idx: int = -1) -> NDArray[np.uint8]:
        """Return a mask of all legal moves for the current player."""
        board = np.zeros((self.board_size, self.board_size), dtype=np.uint8)
        for x, y in self.legal_moves(turn_idx=turn_idx):
            board[self.board_size - y - 1, x] = 1

        return board

    def legal_moves(self, *, turn_idx: int = -1) -> Iterable[Move]:
        """Return a generator over all legal moves for the current player."""
        for x in range(self.board_size):
            for y in range(self.board_size):
                if self.is_legal(Move(x, y), turn_idx=turn_idx):
                    yield Move(x, y)

    def move(self, x: int, y: int, *, check_legal: bool = True):
        """Make a move at (`x`, `y`)."""
        next_board = self.virtual_move(x, y)

        if check_legal:
            # 7. A move consists of coloring an *empty* point one's own color...
            if self.get_color(x, y) != Color.EMPTY:
                raise IllegalMoveError("Cannot place stone on top of an existing stone")

            # 6. A turn is either a pass; or a move that *doesn't repeat* an
            # earlier grid coloring.
            if self.is_repetition(next_board):
                raise IllegalMoveError(
                    "Superko violation: Cannot repeat an earlier board state",
                )

        self.board_states.append(next_board)
        self.moves.append(Move(x, y))

    def play_move(self, move: Optional[Move], *, check_legal: bool = True):
        """Play a `Move` object on the board. Pass `None` to pass."""
        if move is None:
            self.skip_turn()
        else:
            self.move(move.x, move.y, check_legal=check_legal)

    def virtual_move(self, x: int, y: int, *, turn_idx: int = -1) -> NDArray[np.uint8]:
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

        board = self.board_states[turn_idx].copy()
        color = self.current_player()

        # 7. A move consists of coloring an empty point one's own color...
        board[self.board_size - y - 1, x] = color.value

        # ...then clearing the opponent color,
        self._clear_color(board, color.opponent())

        # ...and then clearing one's own color.
        self._clear_color(board, color)
        return board

    def score(self, turn_idx: int = -1) -> Tuple[int, int]:
        """Return the current score of the game as a (black, white) tuple."""
        board = self.board_states[turn_idx]
        black_dists = distance_transform_cdt(
            board != Color.BLACK.value,
            metric="taxicab",
        )
        white_dists = distance_transform_cdt(
            board != Color.WHITE.value,
            metric="taxicab",
        )
        territories, num_territories = label(board == Color.EMPTY.value)

        # 9. A player’s score is the number of points of her color...
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
    def _clear_color(board: NDArray[np.uint8], color: Color):
        """Clear all stones of a given color."""
        # 4. Clearing a color is the process of emptying all points of that
        # color that don’t reach empty.
        dists = distance_transform_cdt(
            board,
            metric="taxicab",  # Compute distances to empty
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
    def from_sgf(cls, sgf_string: str, check_legal: bool = True) -> "Game":
        """Create a `Board` from an SGF string."""
        sgf_string = sgf_string.strip()

        if not sgf_string.startswith("(;FF[4]"):
            raise ValueError("Only FF[4] SGFs are supported")

        game = cls(19)
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

        ascii_a = ord("a")  # 97
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
