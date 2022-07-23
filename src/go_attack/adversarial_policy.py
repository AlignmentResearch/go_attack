"""Classes implementing hardcoded adversarial policies."""
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import IO, ClassVar, Dict, List, Optional, Type

import numpy as np
import sente

from .board_utils import l1_distance, mirror_move, parse_array


class AdversarialPolicy(ABC):
    """Abstract base class for adversarial policies."""

    @abstractmethod
    def next_move(self) -> Optional[sente.Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """


POLICIES: Dict[str, Type["BasicPolicy"]] = {}


@dataclass
class BasicPolicy(AdversarialPolicy, ABC):
    """Base class for adversarial policies that aren't wrappers."""

    name: ClassVar[str]
    game: sente.Game
    color: sente.stone

    def __init_subclass__(cls) -> None:
        """Register the subclass in the POLICIES dict.

        Returns:
            None
        """
        POLICIES[cls.name] = cls
        return super().__init_subclass__()

    def legal_moves(self) -> Sequence[sente.Move]:
        """Return the legal moves for the current player.

        Returns:
            A list of legal moves for the current player.
        """
        raw = self.game.get_legal_moves()
        size = self.game.get_board().get_side()
        return [m for m in raw if m.get_x() < size and m.get_y() < size]

    def legal_move_mask(self) -> np.ndarray:
        """Return an array which is 0 for legal moves and inf for illegal moves.

        Returns:
            A NumPy array of shape (board_size, board_size) with 1s for legal
            moves and 0s for illegal moves.
        """
        size = self.game.get_board().get_side()
        mask = np.full((size, size), np.inf)
        for move in self.legal_moves():
            mask[move.get_x(), move.get_y()] = 0

        # We have to transpose to make it match KataGo's representation
        return mask.T


class EdgePolicy(BasicPolicy):
    """Random moves sampled from outermost available ring of the board."""

    name: ClassVar[str] = "edge"
    randomized: bool = True

    def next_move(self) -> Optional[sente.Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """
        legal_moves = self.legal_moves()
        size = self.game.get_board().get_side()

        coords = [
            (move.get_x(), move.get_y())
            for move in legal_moves
            if move.get_x() < size or move.get_y() < size
        ]
        if not coords:
            return None

        # Only consider vertices that are in the outermost L-inf box
        center = np.array([size // 2, size // 2])
        centered = coords - center
        inf_norm = np.linalg.norm(centered, axis=1, ord=np.inf)
        max_norm = np.max(inf_norm)

        # Randomly select from this box
        if self.randomized:
            coords = random.choice(
                [c for c, n in zip(coords, inf_norm) if n == max_norm],
            )
        else:
            centered = centered[inf_norm == max_norm]
            next_vertex = max(
                centered,
                key=lambda c: np.arctan2(c[1], c[0]),
                default=None,
            )
            coords = next_vertex + center if next_vertex is not None else None

        return sente.Move(*coords, self.color) if coords is not None else None


class MirrorPolicy(BasicPolicy):
    """Adversarial policy that mirrors the board across the y = x diagonal.

    If victim plays exactly on the y = x diagonal, then we mirror across the
    y = -x diagonal. If the mirror position is not legal, we play the closest
    legal move in the L1 distance sense.
    """

    name: ClassVar[str] = "mirror"

    def next_move(self) -> Optional[sente.Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """
        legal_moves = self.legal_moves()
        if not legal_moves:
            return None

        past_moves = self.game.get_current_sequence()
        assert past_moves, "MirrorPolicy cannot play first move"
        assert self.game.get_active_player() == self.color
        opponent = past_moves[-1]

        # Return the closest legal move to the mirror position
        target = mirror_move(opponent, self.game.get_board().get_side())
        return min(legal_moves, key=lambda move: l1_distance(move, target))


class PassingPolicy(BasicPolicy):
    """Adversarial policy that always passes."""

    name: ClassVar[str] = "pass"

    def next_move(self) -> Optional[sente.Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """
        return None  # Pass


class RandomPolicy(BasicPolicy):
    """Adversarial policy that plays random moves."""

    name: ClassVar[str] = "random"

    def next_move(self) -> Optional[sente.Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """
        legal_moves = self.legal_moves()
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

    def next_move(self) -> Optional[sente.Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """
        # It's important to select the right symmetry here; the one that
        # matches Sente's representation is #4.
        self.gtp_stdin.write(b"kata-raw-nn 0\n")
        size = self.game.get_board().get_side()
        policy_dist = parse_array(self.gtp_stdout, "policy", size)

        flat_idx = np.nanargmin(policy_dist)
        x, y = flat_idx % size, flat_idx // size
        return sente.Move(x, y, self.color)


@dataclass
class NonmyopicWhiteBoxPolicy(BasicPolicy):
    """Plays vertices that KataGo predicts the attacker will not own."""

    name: ClassVar[str] = "nonmyopic-whitebox"
    gtp_stdin: IO[bytes]
    gtp_stdout: IO[bytes]

    def next_move(self) -> Optional[sente.Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """
        self.gtp_stdin.write(b"kata-raw-nn 0\n")
        size = self.game.get_board().get_side()
        ownership_dist = parse_array(self.gtp_stdout, "whiteOwnership", size)
        ownership_dist += self.legal_move_mask()

        try:
            flat_idx = np.nanargmin(ownership_dist)
        except ValueError:
            # No legal moves
            return None
        else:
            x, y = flat_idx % size, flat_idx // size
            return sente.Move(x, y, self.color)


@dataclass
class PassingWrapper(AdversarialPolicy):
    """Wrapper that passes if doing so would lead to immediate victory.

    It will also pass if the opponent passed last turn, and we've played
    more than `turns_before_pass` turns.
    """

    inner: BasicPolicy
    turns_before_pass: int = 211

    def next_move(self) -> Optional[sente.Move]:
        """Return the next move to play.

        Returns:
            The adversarial move to play. If None, we pass.
        """
        # Check if the opponent passed last turn
        game = self.inner.game
        past_moves = game.get_current_sequence()
        if not past_moves or past_moves[-1] is not None:
            return self.inner.next_move()

        # Opponent passed last turn.
        # If we're beyond `turns_before_pass`, just pass
        if len(past_moves) > self.turns_before_pass:
            return None

        # Check if passing would lead to immediate victory
        history = game.get_default_sequence()
        game.play(None)
        would_win = game.get_winner() == self.inner.color

        game = sente.Game()  # Undo the virtual pass
        game.play_sequence(history)
        self.inner.game = game

        return None if would_win else self.inner.next_move()
