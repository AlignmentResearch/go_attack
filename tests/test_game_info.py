"""Tests for `go_attack.game_info`."""

import pathlib

import pytest

from go_attack import game_info

THIS_DIR = pathlib.Path(__file__).absolute().parent
TESTDATA_DIR = THIS_DIR / "testdata"
SGF_DIR = TESTDATA_DIR / "visits-truncated"
SGF_SELFPLAY_DIR = TESTDATA_DIR / "victimplay-truncated"


def test_find_sgf_files() -> None:
    """Tests `game_info.find_sgf_files`."""
    expected_result = [SGF_DIR / "A.sgfs", SGF_DIR / "B.sgfs"]
    assert sorted(game_info.find_sgf_files(SGF_DIR)) == sorted(expected_result)

    expected_result += [SGF_SELFPLAY_DIR / "selfplay/t0-s0-d0/sgfs/C.sgfs"]
    assert sorted(game_info.find_sgf_files(TESTDATA_DIR)) == sorted(expected_result)


def test_read_and_concat_all_files() -> None:
    """Tests `game_info.read_and_concat_all_files`."""
    assert len(game_info.read_and_concat_all_files([])) == 0
    result = game_info.read_and_concat_all_files([SGF_DIR / "A.sgfs"])
    assert len(result) == 1
    assert not result[0].endswith("\n")

    paths = [SGF_DIR / "A.sgfs", SGF_DIR / "B.sgfs"]
    result = game_info.read_and_concat_all_files(paths)
    assert len(result) == 2
    assert not any(x.endswith("\n") for x in result)


@pytest.mark.parametrize("sgf_dir", [SGF_DIR, SGF_SELFPLAY_DIR])
def test_parse_game_info(sgf_dir: pathlib.Path) -> None:
    """Tests `game_info.parse_game_info`."""
    sgf_files = game_info.find_sgf_files(sgf_dir)
    sgf_games = game_info.read_and_concat_all_files(sgf_files)

    for sgf_str in sgf_games:
        game = game_info.parse_game_info(sgf_str)
        assert game.sgf_str == sgf_str
        assert game.b_name != game.w_name
        is_adversarial = "victimplay-truncated" in str(sgf_dir)
        assert hasattr(game, "victim_color") == is_adversarial
