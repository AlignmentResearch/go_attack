"""Module to extract game information from SGF files."""

import dataclasses
import os
import pathlib
import re
from typing import Any, Mapping, Optional, Sequence

import tqdm.auto as tqdm
from sgfmill import sgf


def find_sgf_files(root: pathlib.Path) -> Sequence[pathlib.Path]:
    """Finds all SGF files in `root` (recursively)."""
    sgf_paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        sgf_filenames = [x for x in filenames if x.endswith(".sgfs")]
        sgf_paths += [pathlib.Path(dirpath) / x for x in sgf_filenames]
    return sgf_paths


def read_and_concat_all_files(paths: Sequence[pathlib.Path]) -> Sequence[str]:
    """Returns concatenated contents of all files in `paths`."""
    result = []
    for path in tqdm.tqdm(paths):
        with open(path, "r") as f:
            for line in f.readlines():
                result.append(line.strip())
    return result


@dataclasses.dataclass
class GameInfo:
    """Statistics about a Go game."""

    board_size: int
    gtype: str
    start_turn_idx: int
    init_turn_num: int
    used_initial_position: bool

    b_name: str
    w_name: str

    win_color: Optional[str]

    komi: float  # Positive if white has the advantage

    # Number of extra stones black places at start of game,
    # equivalent to the number of white passes at start of game.
    handicap: int

    is_continuation: bool  # Whether game is continuation of previous game

    # Total number of moves (including passes)
    num_moves: int

    # How many times each player passed
    num_b_pass: int
    num_w_pass: int

    ko_rule: str
    score_rule: str
    tax_rule: str
    sui_legal: bool
    has_button: bool
    whb: str  # whiteHandicapBonus
    fpok: bool  # friendly pass ok

    sgf_str: str  # raw sgf string

    @property
    def lose_color(self) -> Optional[str]:
        """Color of loser."""
        return {"b": "w", "w": "b", None: None}[self.win_color]

    @property
    def win_name(self) -> Optional[str]:
        """Name of winning agent."""
        return {"b": self.b_name, "w": self.w_name, None: None}[self.win_color]

    @property
    def lose_name(self) -> Optional[str]:
        """Name of losing agent."""
        return {"b": self.b_name, "w": self.w_name, None: None}[self.lose_color]

    def to_dict(self) -> Mapping[str, Any]:
        """Convert to dict, including @property methods (derived fields)."""
        res = dataclasses.asdict(self)
        for k, v in self.__class__.__dict__.items():
            if isinstance(v, property):
                res[k] = getattr(self, k)
        return res


@dataclasses.dataclass
class AdversarialGameInfo(GameInfo):
    """Statistics about a Go game played between an adversary and victim."""

    victim_color: str
    adv_color: str

    adv_name: str
    adv_steps: int
    adv_win: bool
    adv_minus_victim_score: float  # With komi

    num_adv_pass: int  # Number of time adversary passed in the game
    num_victim_pass: int  # Number of times victim passed in the game

    @property
    def adv_komi(self) -> float:
        """Adversary's komi."""
        return self.komi * {"w": 1, "b": -1}[self.adv_color]

    @property
    def adv_minus_victim_score_wo_komi(self) -> float:
        """Difference between adversary and victim score without komi."""
        return self.adv_minus_victim_score - self.adv_komi


def comment_prop(
    sgf_game: sgf.Sgf_game,
    prop_name: str,
    default: Optional[str] = None,
) -> Optional[str]:
    """Returns `prop_name` property from comment of `sgf_game`, or `default`."""
    comments = sgf_game.root.get("C")
    if prop_name not in comments:
        return default
    return comments.split(f"{prop_name}=")[1].split(",")[0]


def num_pass(col: str, sgf_game: sgf.Sgf_game) -> int:
    """Number of times `color` passes in `sgf_game`."""
    return sum(node.get_move == (col, None) for node in sgf_game.get_main_sequence())


def extract_re(subject: str, pattern: str) -> str:
    """Extract first group matching `pattern` from `subject`."""
    match = re.search(pattern, subject)
    assert match is not None
    return match.group(1)


def extract_basic_game_info(sgf_str: str, sgf_game: sgf.Sgf_game) -> GameInfo:
    """Build `GameInfo` from `sgf_str` and `sgf_game`."""
    rule_str = sgf_game.root.get("RU")

    whb = "0"
    if "whb" in rule_str:
        whb = extract_re(rule_str, r"whb([A-Z0-9\-]+)")

    return GameInfo(
        board_size=sgf_game.get_size(),
        gtype=comment_prop(sgf_game, "gtype"),
        start_turn_idx=int(comment_prop(sgf_game, "startTurnIdx")),
        init_turn_num=int(comment_prop(sgf_game, "initTurnNum")),
        used_initial_position=comment_prop(sgf_game, "usedInitialPosition") == "1",
        b_name=sgf_game.get_player_name("b"),
        w_name=sgf_game.get_player_name("w"),
        win_color=sgf_game.get_winner(),
        komi=sgf_game.get_komi(),
        handicap=int(sgf_game.root.get("HA")),
        is_continuation=sgf_game.get_root().has_setup_stones(),
        num_moves=len(sgf_game.get_main_sequence()) - 1,
        num_b_pass=num_pass("b", sgf_game),
        num_w_pass=num_pass("w", sgf_game),
        sgf_str=sgf_str,
        ko_rule=extract_re(rule_str, r"ko([A-Z]+)"),
        score_rule=extract_re(rule_str, r"score([A-Z]+)"),
        tax_rule=extract_re(rule_str, r"tax([A-Z]+)"),
        sui_legal=extract_re(rule_str, r"sui([0-9])") == "1",
        has_button="button1" in rule_str,
        whb=whb,
        fpok="fpok" in rule_str,
    )


def extract_adversarial_game_info(
    basic_info: GameInfo,
    sgf_game: sgf.Sgf_game,
) -> AdversarialGameInfo:
    """Adds adversarial game info to `basic_info` from `sgf_game`."""
    name_to_color = {basic_info.b_name: "b", basic_info.w_name: "w"}
    victim_color = name_to_color["victim"]
    adv_color = {"b": "w", "w": "b"}[victim_color]
    adv_raw_name = {"b": basic_info.b_name, "w": basic_info.w_name}[adv_color]
    adv_name = (
        adv_raw_name.split("__victim")[0]
        if adv_color == "b"
        else adv_raw_name.split("victim__")[1]
    )
    adv_steps = (
        0 if adv_name == "random" else int(extract_re(adv_name, r"\-s([0-9]+)\-"))
    )

    if basic_info.win_color is None:
        adv_minus_victim_score = 0
    else:
        win_score = float(sgf_game.get_root().get("RE").split("+")[1])
        adv_minus_victim_score = {
            basic_info.win_color: win_score,
            basic_info.lose_color: -win_score,
        }[adv_color]

    num_passes = {"b": basic_info.num_b_pass, "w": basic_info.num_w_pass}

    return AdversarialGameInfo(
        **dataclasses.asdict(basic_info),
        victim_color=victim_color,
        adv_color=adv_color,
        adv_name=adv_name,
        adv_steps=adv_steps,
        adv_win=adv_color == basic_info.win_color,
        adv_minus_victim_score=adv_minus_victim_score,
        num_adv_pass=num_passes[adv_color],
        num_victim_pass=num_passes[victim_color],
    )


def parse_game_info(sgf_str: str) -> GameInfo:
    """Parse game information from `sgf_str`.

    Args:
        sgf_str: A string describing the game in the SGF format.

    Returns:
        An `AdversarialGameInfo` when one of the players is called `'victim'`;
        otherwise, returns a `GameInfo`.
    """
    sgf_game = sgf.Sgf_game.from_string(sgf_str)
    game_info = extract_basic_game_info(sgf_str, sgf_game)

    if "victim" in {game_info.b_name, game_info.w_name}:
        game_info = extract_adversarial_game_info(game_info, sgf_game)

    return game_info
