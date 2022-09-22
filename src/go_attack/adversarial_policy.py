"""Classes implementing hardcoded adversarial policies."""
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import IO, ClassVar, Dict, Optional, Type

import numpy as np

from .board_utils import l1_distance, mirror_move, parse_array
from .go import Color, Game, Move


class AdversarialPolicy(ABC):
    """Abstract base class for adversarial policies."""

    @abstractmethod
    def next_move(self) -> Optional[Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """


POLICIES: Dict[str, Type["BasicPolicy"]] = {}


@dataclass
class BasicPolicy(AdversarialPolicy, ABC):
    """Base class for adversarial policies that aren't wrappers."""

    name: ClassVar[str]
    game: Game
    color: Color
    allow_suicide: bool

    def __init_subclass__(cls) -> None:
        """Register the subclass in the POLICIES dict."""
        POLICIES[cls.name] = cls
        return super().__init_subclass__()


class EdgePolicy(BasicPolicy):
    """Random moves sampled from outermost available ring of the board."""

    name: ClassVar[str] = "edge"
    randomized: bool = True

    def __post_init__(self):  # noqa: D105
        if self.game.board_size % 2 == 0:
            raise ValueError("EdgePolicy only works on odd board sizes")

    def next_move(self) -> Optional[Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """
        legal_moves = list(self.game.legal_moves(allow_suicide=self.allow_suicide))
        size = self.game.board_size

        if not legal_moves:
            return None

        # Only consider vertices that are in the outermost L-inf box
        center = np.array([size // 2, size // 2])
        centered = legal_moves - center
        inf_norm = np.linalg.norm(centered, axis=1, ord=np.inf)
        max_norm = np.max(inf_norm)

        # Randomly select from this box
        if self.randomized:
            coords = random.choice(
                [c for c, n in zip(legal_moves, inf_norm) if n == max_norm],
            )
        else:
            centered = centered[inf_norm == max_norm]
            next_vertex = max(
                centered,
                key=lambda c: np.arctan2(c[1], c[0]),
                default=None,
            )
            coords = next_vertex + center if next_vertex is not None else None

        return Move(*coords) if coords is not None else None


class MirrorPolicy(BasicPolicy):
    """Adversarial policy that mirrors the board across the y = x diagonal.

    If victim plays exactly on the y = x diagonal, then we mirror across the
    y = -x diagonal. If the mirror position is not legal, we play the closest
    legal move in the L1 distance sense. If the opponent passed, we play
    randomly.
    """

    name: ClassVar[str] = "mirror"

    def next_move(self) -> Optional[Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """
        legal_moves = list(self.game.legal_moves(allow_suicide=self.allow_suicide))
        if not legal_moves:
            return None

        past_moves = self.game.moves
        assert past_moves, "MirrorPolicy cannot play first move"
        assert self.game.current_player() == self.color
        opponent = past_moves[-1]
        if opponent is None:  # opponent passed, play randomly
            return random.choice(legal_moves)

        # Return the closest legal move to the mirror position
        tgt = mirror_move(opponent, self.game.board_size)
        return min(legal_moves, key=lambda m: l1_distance(m, tgt))


class PassingPolicy(BasicPolicy):
    """Adversarial policy that always passes."""

    name: ClassVar[str] = "pass"

    def next_move(self) -> Optional[Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """
        return None  # Pass


class RandomPolicy(BasicPolicy):
    """Adversarial policy that plays random moves."""

    name: ClassVar[str] = "random"

    def next_move(self) -> Optional[Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """
        legal_moves = list(self.game.legal_moves(allow_suicide=self.allow_suicide))
        return random.choice(legal_moves) if legal_moves else None


class SpiralPolicy(EdgePolicy):
    """Adversarial policy that plays moves in a spiral pattern."""

    name: ClassVar[str] = "spiral"
    randomized: bool = False


@dataclass
class MyopicWhiteBoxPolicy(BasicPolicy):
    """Plays least likely moves from KataGo's policy net."""

    name: ClassVar[str] = "myopic-whitebox"
    gtp_stdin: IO[bytes]
    gtp_stdout: IO[bytes]

    def next_move(self) -> Optional[Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """
        self.gtp_stdin.write(b"kata-raw-nn 0\n")
        size = self.game.board_size
        policy_dist = parse_array(self.gtp_stdout, "policy", size)

        try:
            flat_idx = np.nanargmin(policy_dist)
        except ValueError:  # No legal moves
            return None
        else:
            x, y = flat_idx % size, flat_idx // size
            return Move(x, y)


@dataclass
class NonmyopicWhiteBoxPolicy(BasicPolicy):
    """Plays vertices that KataGo predicts the attacker will not own."""

    name: ClassVar[str] = "nonmyopic-whitebox"
    gtp_stdin: IO[bytes]
    gtp_stdout: IO[bytes]

    def next_move(self) -> Optional[Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """
        self.gtp_stdin.write(b"kata-raw-nn 0\n")
        size = self.game.board_size
        ownership_dist = parse_array(self.gtp_stdout, "whiteOwnership", size)
        ownership_dist += (1 - self.game.legal_move_mask(allow_suicide=self.allow_suicide).T) * np.inf

        try:
            flat_idx = np.nanargmin(ownership_dist)
        except ValueError:
            # No legal moves
            return None
        else:
            x, y = flat_idx % size, flat_idx // size
            return Move(x, y)  # type: ignore


@dataclass
class PassingWrapper(AdversarialPolicy):
    """Wrapper that passes if doing so would lead to immediate victory.

    It will also pass if the opponent passed last turn, and we've played
    more than `moves_before_pass` turns.
    """

    inner: BasicPolicy
    moves_before_pass: int = 211

    def next_move(self) -> Optional[Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """
        # Check if the opponent passed last turn
        game = self.inner.game
        past_moves = game.moves
        if not past_moves or past_moves[-1] is not None:
            return self.inner.next_move()

        # Opponent passed last turn.
        # If we're beyond `moves_before_pass`, just pass
        if len(past_moves) > self.moves_before_pass:
            return None

        # Check if passing would lead to immediate victory
        game.skip_turn()
        would_win = game.winner() == self.inner.color
        game.undo()

        return None if would_win else self.inner.next_move()
