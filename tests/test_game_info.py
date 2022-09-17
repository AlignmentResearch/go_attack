"""Tests for `go_attack.game_info`."""

import pathlib

import pytest

from go_attack.game_info import (
    find_sgf_files,
    read_and_parse_all_files,
    read_and_parse_file,
)

THIS_DIR = pathlib.Path(__file__).absolute().parent
TESTDATA_DIR = THIS_DIR / "testdata"
SGF_DIR = TESTDATA_DIR / "visits-truncated"
SGF_SELFPLAY_DIR = TESTDATA_DIR / "victimplay-truncated"


def test_find_sgf_files() -> None:
    """Tests `game_info.find_sgf_files`."""
    expected_result = [SGF_DIR / "A.sgfs", SGF_DIR / "B.sgfs"]
    assert sorted(find_sgf_files(SGF_DIR)) == sorted(expected_result)

    expected_result += [SGF_SELFPLAY_DIR / "selfplay/t0-s0-d0/sgfs/C.sgfs"]
    assert sorted(find_sgf_files(TESTDATA_DIR)) == sorted(expected_result)


def test_parse_game_info() -> None:
    """Smoke test to check parsing works."""
    path = SGF_DIR / "A.sgfs"
    sgf_game = read_and_parse_file(path, fast_parse=False)[0]
    assert sgf_game["b_name"] == "cp63-v1024__victim"
    assert sgf_game["sgf_path"] == str(path)
    assert sgf_game["sgf_line"] == 1
    print(sgf_game)


@pytest.mark.parametrize("sgf_dir", [SGF_DIR, SGF_SELFPLAY_DIR])
def test_slow_and_fast_parse(sgf_dir: pathlib.Path) -> None:
    """Check the correct properties are extracted in fast and slow parsing."""
    sgf_files = find_sgf_files(sgf_dir)
    slow_parsed_sgf_games = read_and_parse_all_files(
        sgf_files,
        fast_parse=False,
    )
    for sgf_game in slow_parsed_sgf_games:
        assert "adv_color" in sgf_game
        assert "num_b_pass" in sgf_game
        assert "num_victim_pass" in sgf_game
        assert "w_name" in sgf_game

    slow_parsed_sgf_games = read_and_parse_all_files(
        sgf_files,
        fast_parse=True,
    )
    for sgf_game in slow_parsed_sgf_games:
        assert "adv_color" in sgf_game
        assert "num_b_pass" not in sgf_game
        assert "num_victim_pass" not in sgf_game
        assert "w_name" not in sgf_game
