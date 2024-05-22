#!/usr/bin/python3

"""Curriculum module for using in victimplay."""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import enum
import json
import logging
import os
import pathlib
import re
import shutil
import sys
import time
from typing import Any, ClassVar, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from sgfmill import sgf

Config = Mapping[str, Any]


@enum.unique
class Color(enum.Enum):
    """Color of Go stones (black or white)."""

    BLACK = "B"
    WHITE = "W"

    @staticmethod
    def from_string(color: str) -> "Color":
        color = color.upper()
        return Color(color)


def flip_color(color: Color) -> Color:
    if color == Color.BLACK:
        return Color.WHITE
    elif color == Color.WHITE:
        return Color.BLACK
    else:
        raise TypeError(f"Color must be black or white, not {color}")


@dataclasses.dataclass(frozen=True)
class AdvGameInfo:
    """Class for storing game result from the adversary perspective."""

    board_size: int
    victim_name: str
    victim_visits: int
    adv_visits: int
    game_hash: str
    winner: Optional[bool]
    score_diff: float
    score_wo_komi_diff: float
    is_selfplay: bool


class DataClassBase(object):
    """No-op class needed as a base for dataclasses in multiple composition."""

    def __post_init__(self):
        pass


@dataclasses.dataclass(frozen=True)
class PlayerStat(DataClassBase):
    """Class for storing game statistics.

    Statistics is being represented from the adversary perspective.
    """

    name: Optional[str] = None
    win_rate: Optional[float] = None
    score_diff: Optional[float] = None
    score_wo_komi_diff: Optional[float] = None
    policy_loss: Optional[float] = None

    def get_stat_members(self) -> Dict[str, float]:
        """Returns members of PlayerStat except name, excluding fields in subclsses."""
        d = dataclasses.asdict(self)
        fields = (f.name for f in dataclasses.fields(PlayerStat))
        return {k: d[k] for k in fields if k != "name"}


@dataclasses.dataclass(frozen=True)
class VictimParams(DataClassBase):
    """Parameters associated with an attack against a victim."""

    name: str
    max_visits_victim: Optional[int] = None
    max_visits_adv: Optional[int] = None

    def matches_criteria(
        self,
        other: VictimParams,
        strict: bool = True,
    ) -> bool:
        """Check two VictimParams objects agree.

        Compares only the fields defined in VictimParams; intentionally
        ignores fields defined in subclasses.

        Args:
            other: A VictimParams object.
            strict: If False, None entries in `self` always compare equal;
                if True, only compares equal to None.

        Returns:
            True if the above fields compare equal; False otherwise.
        """
        d0 = dataclasses.asdict(self)
        d1 = dataclasses.asdict(other)

        fields = (f.name for f in dataclasses.fields(VictimParams))
        return all(d0[f] == d1[f] or (not strict and d0[f] is None) for f in fields)


@dataclasses.dataclass(frozen=True)
class VictimCriteria(PlayerStat, VictimParams):
    """Criteria for the victim change.

    Victim is represented by the model name and max visits.
    Criteria are represented by the statistics members.
    For victim only one criterion can be enabled, all others should be None.
    """

    def __post_init__(self):
        if self.name is None:
            raise ValueError("VictimCriteria: victim name is None")
        criteria = self.get_stat_members()
        enabled_criteria = [v for k, v in criteria.items() if v is not None]
        num_enabled = len(enabled_criteria)
        if num_enabled != 1:
            msg = f"Need 1 criteria enabled, got {num_enabled}: {enabled_criteria}"
            raise ValueError(msg)

    # check if adv_stat has a greater value of enabled criteria
    def check_if_gt(self, adv_stat: PlayerStat) -> bool:
        criteria = self.get_stat_members()
        adv_vals = adv_stat.get_stat_members()
        for k, v in criteria.items():
            if v is not None:
                logging.info(
                    "{}: {} (adv) <-> {} (threshold)".format(k, adv_vals[k], v),
                )
                if adv_vals[k] > v:
                    return True
        return False


def is_name_victim(name: str) -> bool:
    """Has 'victim-' in `name` and not a colored evaluator."""
    return "victim-" in name and "__" not in name


def get_game_hash(game: sgf.Sgf_game) -> Optional[str]:
    """Extracts the hash from the game comment field C."""
    # game_c = startTurnIdx=N,initTurnNum=N,gameHash=X
    try:
        game_c = game.get_root().get("C")
    except KeyError:
        logging.warning("No comment field in game %s", game, exc_info=True)
        return None
    # game_hash_raw: gameHash=X
    game_hash_raw = game_c.split(",")[2]
    # Returns the hash X
    return game_hash_raw.split("=")[1]


def get_game_score(game: sgf.Sgf_game) -> Optional[float]:
    try:
        result = game.get_root().get("RE")
    except KeyError:
        # No RE[] tag may be because the game hit its move limit
        return None
    try:
        win_score = result.split("+")[1]
    except IndexError:
        logging.warning("No winner in result '%s'", result, exc_info=True)
        return None
    try:
        win_score = float(win_score)
    except ValueError:
        logging.warning("Game score is not numeric: '%s'", win_score, exc_info=True)
        return None
    return win_score


def get_victim_adv_colors(game: sgf.Sgf_game) -> Tuple[str, Color, Color]:
    """Returns a tuple of victim name, victim color and adversary color."""
    colors: Sequence[Color] = (Color.BLACK, Color.WHITE)
    name_to_colors: Mapping[str, Color] = {
        game.get_player_name(color.value.lower()): color for color in colors
    }
    victim_names = [name for name in name_to_colors.keys() if is_name_victim(name)]
    if len(victim_names) != 1:
        raise ValueError("Found '{len(victim_names)}' != 1 victims: %s", victim_names)
    victim_name = victim_names[0]
    assert victim_name.startswith("victim-")

    victim_color = name_to_colors[victim_name]
    adv_color = flip_color(victim_color)

    victim_name = victim_name[7:]
    return victim_name, victim_color, adv_color


def get_max_visits(game: sgf.Sgf_game, color: Color) -> int:
    """Get max visits for player `color` in `game`."""
    visit_key = color.value + "R"  # BR or WR: black/white rank
    visit_string = game.get_root().get(visit_key)
    visit_num = re.search("v=([0-9]+)", visit_string)
    if not visit_num:
        raise ValueError(f"Could not find visit count in '{visit_string}'")

    return int(visit_num[1])


def is_selfplay_game(game: sgf.Sgf_game) -> bool:
    """Returns true if the game is a selfplay game for the adversary."""
    colors = (Color.BLACK, Color.WHITE)
    player_names = [game.get_player_name(color.value.lower()) for color in colors]
    if player_names[0] != player_names[1]:
        return False
    if is_name_victim(player_names[0]):
        return False
    if get_max_visits(game, Color.BLACK) != get_max_visits(game, Color.WHITE):
        return False
    return True


def get_game_info(sgf_str: str) -> Optional[AdvGameInfo]:
    try:
        game = sgf.Sgf_game.from_string(sgf_str)
    except ValueError:
        logging.warning("Error parsing game: '%s'", sgf_str, exc_info=True)
        return None

    game_hash = get_game_hash(game)
    if game_hash is None:
        return None

    if is_selfplay_game(game):
        return AdvGameInfo(
            board_size=game.get_size(),
            victim_name="",
            victim_visits=0,
            adv_visits=get_max_visits(game, Color.BLACK),
            game_hash=game_hash,
            winner=None,
            score_diff=0,
            score_wo_komi_diff=0,
            is_selfplay=True,
        )

    victim_name, victim_color, adv_color = get_victim_adv_colors(game)
    victim_visits = get_max_visits(game, victim_color)
    adv_visits = get_max_visits(game, adv_color)

    komi = game.get_komi()
    adv_komi = komi if adv_color == Color.WHITE else -komi

    win_score = get_game_score(game)
    if win_score is None:
        # either the game tied (which should never happen under default rules)
        # or the game hit the move limit
        adv_minus_victim_score = 0
        adv_minus_victim_score_wo_komi = 0
        winner = None
    else:
        win_color = Color.from_string(game.get_winner())
        winner = win_color == adv_color
        adv_minus_victim_score = win_score if winner else -win_score
        adv_minus_victim_score_wo_komi = adv_minus_victim_score - adv_komi

    return AdvGameInfo(
        board_size=game.get_size(),
        victim_name=victim_name,
        victim_visits=victim_visits,
        adv_visits=adv_visits,
        game_hash=game_hash,
        winner=winner,
        score_diff=adv_minus_victim_score,
        score_wo_komi_diff=adv_minus_victim_score_wo_komi,
        is_selfplay=False,
    )


def get_files_sorted_by_modification_time(
    folder: pathlib.Path,
    extension: Optional[str] = None,
    ignore_extensions: Optional[Sequence[str]] = None,
) -> Sequence[str]:
    all_files = []
    for path, dirnames, filenames in os.walk(folder, followlinks=True):
        for f in filenames:
            ext = os.path.splitext(f)[1]
            if ignore_extensions is not None and ext in ignore_extensions:
                continue
            if extension is None or ext == extension:
                file_path = os.path.join(path, f)
                all_files.append([file_path, os.path.getmtime(file_path)])
    # sort from newest to oldest
    all_files.sort(key=lambda x: x[1], reverse=True)

    # leave file names only
    return [x[0] for x in all_files]


def filter_games(
    games: Iterable[AdvGameInfo],
    current_victim: VictimCriteria,
) -> Sequence[AdvGameInfo]:
    """Returns the subset of `games` corresponding to the `current_victim`."""
    filtered_games = []
    for game in games:
        victim_params = VictimParams(
            name=game.victim_name,
            max_visits_victim=game.victim_visits,
            max_visits_adv=game.adv_visits,
        )
        if current_victim.matches_criteria(victim_params, strict=False):
            filtered_games.append(game)
    return filtered_games


def recompute_statistics(games: Sequence[AdvGameInfo]) -> Optional[PlayerStat]:
    """Compute statistics from `games`."""
    logging.info("Computing {} games".format(len(games)))

    sum_wins = 0
    sum_ties = 0
    sum_score = 0
    sum_score_wo_komi = 0
    for game in games:
        # game.winner can be None (for ties), but a tie is still not a win
        if game.winner:
            sum_wins += 1
        elif game.winner is None:
            sum_ties += 1
        sum_score += game.score_diff
        sum_score_wo_komi += game.score_wo_komi_diff

    logging.info(
        "Got {} wins and {} ties from {} games".format(sum_wins, sum_ties, len(games)),
    )
    win_rate = sum_wins / len(games)
    mean_diff_score = sum_score / len(games)
    mean_diff_score_wo_komi = sum_score_wo_komi / len(games)

    return PlayerStat(
        name=game.victim_name,
        win_rate=win_rate,
        score_diff=mean_diff_score,
        score_wo_komi_diff=mean_diff_score_wo_komi,
    )


def parse_config(config: Sequence[Config]) -> Sequence[VictimCriteria]:
    """Parse `config` into a sequence of VictimCriteria, ignoring comments."""
    victims = []
    for line in config:
        line = dict(line)
        line.pop("_comment", None)  # delete _comment if it exists
        try:
            cond = VictimCriteria(**line)
        except ValueError as e:
            raise ValueError(f"Invalid victim config '{line}'") from e
        victims.append(cond)
    return victims


class Curriculum:
    """Curriculum object.

    Curriculum is used for updating victims for victimplay based on
    the criteria specified in the provided config.
    """

    MAX_VICTIM_COPYING_EFFORTS: ClassVar[int] = 10
    VICTIM_COPY_FILESYSTEM_ACCESS_TIMEOUT: ClassVar[int] = 10
    BOARD_SIZE_FILTER: ClassVar[int] = 19
    SELFPLAY_CONFIG_OVERRIDE_NAME: ClassVar[str] = "victim.cfg"

    def __init__(
        self,
        victims_input_dir: pathlib.Path,
        victims_output_dir: pathlib.Path,
        config: Sequence[Config],
        stats_rolling_window: int,
        game_buffer_capacity: int,
        # Defaults to 0 (no victims are hardened)
        harden_below_visits: int = 0,
    ):
        """Initial curriculum setup.

        Construct and initialize curriculum.

        Args:
            victims_input_dir: The folder with all victim model
                files specified in the config.
            victims_output_dir: The folder where we copy victims for selfplay.
            config: Sequence of victim configurations.
            stats_rolling_window: The number of most recent games from the current
                victim used for computing statistics. The curriculum will not move
                past the victim until at least this many games has been collected.
            game_buffer_capacity: The maximum number of games to store in the buffer.
                This consists of all games, not just those matching the current victim.
            harden_below_visits: Harden the victim when its visits are at most
                this amount.

        Raises:
            ValueError: `game_buffer_capacity` is less than `min_games_for_stats`.
        """
        self.stat_files = []
        self.sgf_games = []
        self.game_hashes = {}
        self.finished = False

        self.victims_input_dir = victims_input_dir
        self.victims_output_dir = victims_output_dir
        self.selfplay_config_override_path = (
            victims_output_dir / self.SELFPLAY_CONFIG_OVERRIDE_NAME
        )
        self.victims_output_dir_tmp = victims_output_dir.with_name(
            victims_output_dir.name + "_tmp",
        )
        self.stats_rolling_window = stats_rolling_window
        self.game_buffer_capacity = game_buffer_capacity
        if self.game_buffer_capacity < self.stats_rolling_window:
            msg = "Game buffer smaller than statistics rolling window: "
            msg += f"{self.game_buffer_capacity} < {self.stats_rolling_window}"
            raise ValueError(msg)
        self.harden_below_visits = harden_below_visits

        # Parse config
        self.victims = parse_config(config)
        logging.info("Loaded curriculum with the following params:")
        logging.info("\n".join([str(x) for x in config]))

        # Make sure that all the victims exist
        for victim in self.victims:
            assert victim.name is not None
            victim_ckpt = victims_input_dir / victim.name
            if not victim_ckpt.exists():
                raise ValueError(f"Victim checkpoint {victim_ckpt} does not exist")

        # Try to restart training from the latest victim if we've previously been run
        self.victim_idx = 0
        latest_victim_params = self._load_latest_victim_params()
        if latest_victim_params is not None:
            self.victim_idx = self._match_victim_params(latest_victim_params)

        logging.info(
            "Copying the latest victim '{}'...".format(self._cur_victim),
        )
        self._try_victim_copy()

        # Maybe also warmstart the predictor with the victim
        predictor_dir = victims_output_dir.parent / "predictor"
        if predictor_dir.exists():
            logging.info("Warm starting predictor with victim network...")
            models_dir = predictor_dir / "models" / "bootstrap"
            models_dir.mkdir(exist_ok=True, parents=True)
            self._try_victim_copy(dest_dir=models_dir, dest_name="model.bin.gz")

        logging.info("Curriculum initial setup is complete")

    def _load_latest_victim_params(self) -> Optional[VictimParams]:
        """Loads the parameters of the latest victim from disk."""
        logging.info("Finding the latest victim...")
        victim_files = get_files_sorted_by_modification_time(
            self.victims_output_dir,
            ignore_extensions=(".cfg", ".conf"),
        )
        if victim_files:
            last_victim_name = os.path.basename(victim_files[0])
            max_visits_victim = None
            max_visits_adv = None

            # find current maxVisits settings
            if os.path.exists(self.selfplay_config_override_path):
                with open(self.selfplay_config_override_path) as f:
                    for line in f.readlines():
                        line = line.strip()
                        if not line:
                            continue
                        name, val = line.split("=")
                        if name == "maxVisits0":
                            max_visits_victim = int(val)
                        elif name == "maxVisits1":
                            max_visits_adv = int(val)

            return VictimParams(
                name=last_victim_name,
                max_visits_victim=max_visits_victim,
                max_visits_adv=max_visits_adv,
            )

    def _match_victim_params(self, victim_params: VictimParams) -> int:
        # determine current victim-with-max-visits index
        for cur_idx in range(len(self.victims)):
            if self.victims[cur_idx].matches_criteria(victim_params):
                return cur_idx

        logging.warning(
            "Victim '{}' is not found in '{}', starting from scratch".format(
                str(victim_params),
                self.victims_output_dir,
            ),
        )
        return 0

    @property
    def _cur_victim(self) -> VictimCriteria:
        return self.victims[self.victim_idx]

    def _update_victim_config(self):
        tmp_path = self.victims_output_dir_tmp / self.SELFPLAY_CONFIG_OVERRIDE_NAME
        with open(tmp_path, "w") as f:
            if self._cur_victim.max_visits_victim is not None:
                f.write(f"maxVisits0={self._cur_victim.max_visits_victim}\n")
                if self._cur_victim.max_visits_victim <= self.harden_below_visits:
                    f.write("passingBehavior0=avoid-pass-alive-territory\n")
            if self._cur_victim.max_visits_adv is not None:
                f.write(f"maxVisits1={self._cur_victim.max_visits_adv}\n")
        shutil.move(str(tmp_path), self.selfplay_config_override_path)

    def _try_victim_copy(self, force_if_exists=False, dest_dir=None, dest_name=None):
        dest_dir = dest_dir or self.victims_output_dir
        victim_name = self._cur_victim.name
        victim_path = dest_dir / (dest_name or victim_name)
        victim_path_tmp = self.victims_output_dir_tmp / victim_name

        if not force_if_exists and os.path.exists(victim_path):
            return

        # Attempt to copy
        for _ in range(self.MAX_VICTIM_COPYING_EFFORTS):
            try:
                # Make sure directories exist
                os.makedirs(dest_dir, exist_ok=True)
                os.makedirs(self.victims_output_dir_tmp, exist_ok=True)
                self._update_victim_config()

                # We copy to a tmp directory then move to make the overall
                # operation atomic, which is needed to avoid race conditions
                # with the C++ code.
                shutil.copy(
                    self.victims_input_dir / victim_name,
                    victim_path_tmp,
                )
                shutil.move(str(victim_path_tmp), victim_path)
                return
            except OSError:
                logging.exception(
                    "Cannot copy victim '{}', maybe "
                    "filesystem problem? Waiting {} sec...".format(
                        self._cur_victim.name,
                        self.VICTIM_COPY_FILESYSTEM_ACCESS_TIMEOUT,
                    ),
                )
                time.sleep(self.VICTIM_COPY_FILESYSTEM_ACCESS_TIMEOUT)

        raise RuntimeError(
            "Problem copying victim '{}', curriculum stopped".format(
                self._cur_victim.name,
            ),
        )

    def try_move_on(
        self,
        adv_stat: PlayerStat,
        policy_loss: Optional[float] = None,
    ):
        if self.finished:
            return

        logging.info("Checking whether we need to move to the next victim...")
        want_victim_update = False
        if self._cur_victim.check_if_gt(adv_stat):
            want_victim_update = True
        if policy_loss is not None:
            raise NotImplementedError("Policy loss check is not implemented yet")

        if not want_victim_update:
            return

        self.victim_idx += 1
        if self.victim_idx == len(self.victims):
            self.finished = True
            return

        logging.info("Moving to the next victim '{}'".format(self._cur_victim.name))
        self._try_victim_copy(True)

    def update_sgf_games(self, selfplay_dir: pathlib.Path):
        all_sgfs = get_files_sorted_by_modification_time(selfplay_dir, ".sgfs")

        useful_files = set()
        cur_games = []
        num_selfplay_games = 0
        for sgf_file in all_sgfs:
            if sgf_file not in self.game_hashes:
                self.game_hashes[sgf_file] = set()

            with open(sgf_file) as f:
                logging.debug("Processing SGF file '{}'".format(sgf_file))
                all_lines = list(f.readlines())

                for line in reversed(all_lines):
                    if not line.endswith("\n"):  # game not fully written
                        continue
                    sgf_string = line.strip()
                    game_stat = get_game_info(sgf_string)
                    if game_stat is None:
                        continue
                    if game_stat.board_size != Curriculum.BOARD_SIZE_FILTER:
                        continue

                    # game hash was found, so consider that the rest of them are older
                    # so stop scanning this file
                    if game_stat.game_hash in self.game_hashes[sgf_file]:
                        break
                    self.game_hashes[sgf_file].add(game_stat.game_hash)

                    if game_stat.is_selfplay:
                        num_selfplay_games += 1
                        continue

                    cur_games.append(game_stat)
                    useful_files.add(sgf_file)

        # now have cur_games sorted from newer to older
        games_log_message = (
            f"Got {len(cur_games)} new games from {len(useful_files)} files"
        )
        if num_selfplay_games > 0:
            games_log_message += f", ignored {num_selfplay_games} selfplay games"
        logging.info(games_log_message)
        for f in useful_files:
            logging.info("Useful SGF file: '{}'".format(str(f)))

        # insert new games in the beginning
        self.sgf_games[:0] = cur_games

        # leave only game_buffer_capacity games for statistics computation
        # so delete some old games
        if len(self.sgf_games) > self.game_buffer_capacity:
            del self.sgf_games[self.game_buffer_capacity :]

    """
    Run curriculum checking.
    @param selfplay_dir: Folder with selfplay results.
    @param games_for_compute: Number of games to compute statistics.
    @param checking_periodicity: Checking interval in seconds.
    """

    def checking_loop(
        self,
        selfplay_dir: pathlib.Path,
        checking_periodicity: int,
    ):
        logging.info("Starting curriculum loop")
        while True:
            self.update_sgf_games(selfplay_dir)
            filtered_games = filter_games(
                self.sgf_games,
                self._cur_victim,
            )
            if len(filtered_games) < self.stats_rolling_window:
                msg = "Incomplete statistics for current victim, got only "
                msg += f"{len(filtered_games)} < {self.stats_rolling_window} "
                logging.info(msg)
            else:
                # new games are added to front of `self.sgf_games`
                most_recent_games = filtered_games[: self.stats_rolling_window]
                adv_stat = recompute_statistics(most_recent_games)
                self.try_move_on(adv_stat=adv_stat)

            if self.finished:
                logging.info("Curriculum is done. Stopping")
                break

            logging.info(
                "Curriculum is alive, current victim : {} @ v{} w/ adv @ v{}".format(
                    self._cur_victim.name,
                    self._cur_victim.max_visits_victim,
                    self._cur_victim.max_visits_adv,
                ),
            )
            time.sleep(checking_periodicity)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run victim replacement based on win rate.",
    )
    parser.add_argument(
        "-selfplay-dir",
        type=pathlib.Path,
        required=True,
        help="Directory with selfplay data",
    )
    parser.add_argument(
        "-input-models-dir",
        type=pathlib.Path,
        required=True,
        help="Input dir with victim model files",
    )
    parser.add_argument(
        "-output-models-dir",
        type=pathlib.Path,
        required=True,
        help="Output dir for adding new victims",
    )
    parser.add_argument(
        "-stats-rolling-window",
        type=int,
        required=False,
        default=1000,
        help="Number of games from current victim to average statistics over",
    )
    parser.add_argument(
        "-max-games-buffer",
        type=int,
        required=False,
        default=10000,
        help="Maximum number of games to store in FIFO buffer",
    )
    parser.add_argument(
        "-checking-periodicity",
        type=int,
        required=False,
        default=60,
        help="Statistics computation periodicity in seconds",
    )
    parser.add_argument(
        "-config-json-string",
        required=False,
        help="Curriculum JSON config with " "victims sequence (JSON content)",
    )
    parser.add_argument(
        "-config-json-file",
        type=pathlib.Path,
        default="configs/curriculum_conf.json",
        help="Curriculum JSON config with " "victims sequence (JSON file path)",
    )
    # From a UI standpoint it makes more sense to be able to specify in the JSON
    # config whether hardening is desired for each victim. Adding a flag to
    # harden at low victim visit counts is easier to implement though, and it
    # covers the main way we use hardening during training.
    parser.add_argument(
        "-harden-below-visits",
        type=int,
        default=0,
        help="Enable pass-alive hardening when victim has at most this many visits",
    )
    parser.add_argument(
        "-d",
        "--debug",
        help="Set log level to DEBUG (default INFO)",
        action="store_const",
        dest="log_level",
        const=logging.DEBUG,
        default=logging.INFO,
    )

    return parser.parse_args()


def setup_logging(selfplay_dir: str, log_level: int) -> None:
    """Setup logging to file {selfplay_dir}/curriculum-<timestamp>.log and stdout."""
    pathlib.Path(selfplay_dir).mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    timestamp = datetime.datetime.utcnow().isoformat()
    file_handler = logging.FileHandler(
        filename=f"{selfplay_dir}/curriculum-{timestamp}.log",
    )
    stdout_handler = logging.StreamHandler(stream=sys.stdout)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stdout_handler)


def make_curriculum(args: argparse.Namespace) -> Curriculum:
    """Construct curriculum from CLI `args`."""
    if args.config_json_string is not None:
        logging.info("Curriculum: loading JSON config from a string")
        config = json.loads(args.config_json)
    else:
        logging.info(f"Curriculum: loading JSON config from '{args.config_json_file}'")
        with open(args.config_json_file) as f:
            config = json.load(f)

    return Curriculum(
        victims_input_dir=args.input_models_dir,
        victims_output_dir=args.output_models_dir,
        config=config,
        stats_rolling_window=args.stats_rolling_window,
        game_buffer_capacity=args.max_games_buffer,
        harden_below_visits=args.harden_below_visits,
    )


def main():
    """Main console entry point to script."""
    args = parse_args()
    setup_logging(args.selfplay_dir, args.log_level)
    curriculum = make_curriculum(args)

    try:
        curriculum.checking_loop(
            args.selfplay_dir,
            args.checking_periodicity,
        )
    # we really want to silence 'B902: blind except'
    # because we want a stacktrace and error description in logs
    except BaseException as e:  # noqa: B902
        logging.exception("Curriculum error: {}".format(e))
        raise

    logging.info("Curriculum finished!")


if __name__ == "__main__":
    main()
