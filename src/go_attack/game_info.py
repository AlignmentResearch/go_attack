"""Module to extract game information from SGF files."""

import multiprocessing
import os
import pathlib
import re
from itertools import chain
from typing import Any, Dict, Optional, Sequence


def get_game_str(path: pathlib.Path, line_num: int):
    """Return the string at a given path and line number."""
    with open(path, "r") as f:
        for i, line in enumerate(f):
            if i + 1 == line_num:
                return line


def find_sgf_files(
    root: pathlib.Path,
    max_scan_length: int = 10000,
) -> Sequence[pathlib.Path]:
    """Finds all SGF files in `root` (recursively).

    Args:
        root: The root directory to search.
        max_scan_length: The maximum number of directories to search.

    Returns:
        List of sgf paths.
    """
    sgf_paths = []
    directories_scanned = 0
    for dirpath, _, filenames in os.walk(root):
        sgf_filenames = [x for x in filenames if x.endswith(".sgfs")]
        sgf_paths += [pathlib.Path(dirpath) / x for x in sgf_filenames]
        directories_scanned += 1
        if directories_scanned >= max_scan_length:
            break
    return sgf_paths


def read_and_parse_file(
    path: pathlib.Path,
    fast_parse: bool = False,
) -> Sequence[Dict[str, Any]]:
    """Parse all lines of an sgf file to a list of dictionaries with game info."""
    parsed_games = []
    with open(path, "r") as f:
        for i, line in enumerate(f):
            parsed_games.append(
                parse_game_str_to_dict(
                    str(path),
                    i + 1,
                    line.strip(),
                    fast_parse=fast_parse,
                ),
            )
    return parsed_games


def read_and_parse_file_fast(path: pathlib.Path) -> Sequence[Dict[str, Any]]:
    """Only top level function can be pickled. Used for multiprocessing."""
    return read_and_parse_file(path, fast_parse=True)


def read_and_parse_file_slow(path: pathlib.Path) -> Sequence[Dict[str, Any]]:
    """Only top level function can be pickled. Used for multiprocessing."""
    return read_and_parse_file(path, fast_parse=False)


def read_and_parse_all_files(
    paths: Sequence[pathlib.Path],
    fast_parse: bool = False,
    processes: Optional[int] = None,
) -> Sequence[Dict[str, Any]]:
    """Returns concatenated contents of all files in `paths`."""
    if not processes:
        processes = min(128, len(paths) // 2)
    with multiprocessing.Pool(processes=max(processes, 1)) as pool:
        if fast_parse:
            parsed_games = pool.map(read_and_parse_file_fast, paths)
        else:
            parsed_games = pool.map(read_and_parse_file_slow, paths)

    return list(chain.from_iterable(parsed_games))


def extract_re(pattern: str, subject: str) -> Optional[str]:
    """Extract first group matching `pattern` from `subject`."""
    match = re.search(pattern, subject)
    return match.group(1) if match is not None else None


def extract_prop(property_name: str, sgf_str: str) -> Optional[str]:
    """Extract a property. Eg. PW[white_player]."""
    return extract_re(f"{property_name}\\[([^]]+?)]", sgf_str)


def extract_comment_prop(property_name: str, sgf_str: str) -> Optional[str]:
    """Extract property from a comment. Eg. C[startTurnIdx=0]."""
    return extract_re(f"{property_name}=([^,\\]]+)", sgf_str)


num_b_pass_pattern = re.compile("B\\[]")
num_w_pass_pattern = re.compile("W\\[]")
semicolon_pattern = re.compile(";")


def parse_game_str_to_dict(
    path: str,
    line_number: int,
    sgf_str: str,
    fast_parse: bool = False,
) -> Dict[str, Any]:
    """Parse an sgf string to a dictionary containing game_info.

    Args:
        path: Path where this string was read from. We want to keep this
            information so that we can later retrieve the original string.
        line_number: Line number in the above path.
        sgf_str: The string to parse.
        fast_parse: Include additional fields that are slower to extract
            or generally less useful.

    Returns:
        Dictionary containing game_info.
    """
    rule_str = extract_prop("RU", sgf_str)
    comment_str = extract_prop("C", sgf_str)
    size_str = extract_prop("SZ", sgf_str)
    board_size = int(size_str.split(":")[0]) if size_str else None
    whb = "0"
    if rule_str and "whb" in rule_str:
        whb = extract_re(r"whb([A-Z0-9\-]+)", rule_str)
    b_name = extract_prop("PB", sgf_str)
    w_name = extract_prop("PW", sgf_str)
    result = extract_prop("RE", sgf_str)
    komi = float(extract_prop("KM", sgf_str))
    win_color = result[0].lower() if result else None
    assert (
        "__victim" in b_name or "victim__" in w_name
    ), f"Game doesn't have victim: path={path}, line_number={line_number}"

    adv_color = "w" if "victim__" in w_name else "b"
    adv_raw_name = b_name if adv_color == "b" else w_name
    adv_name = (
        adv_raw_name.split("__victim")[0]
        if adv_color == "b"
        else adv_raw_name.split("victim__")[-1]
    )
    if win_color is None:
        adv_minus_victim_score = 0
    else:
        win_score = float(result.split("+")[-1])
        adv_minus_victim_score = win_score if adv_color == win_color else -win_score
    adv_steps_str = extract_re(r"\-s([0-9]+)\-", adv_name)
    adv_samples_str = extract_re(r"\-d([0-9]+)", adv_name)
    adv_komi = komi * {"w": 1, "b": -1}[adv_color]

    parsed_info = {
        "adv_win": adv_color == win_color,
        "adv_minus_victim_score": adv_minus_victim_score,
        "board_size": board_size,
        "adv_steps": int(adv_steps_str) if adv_steps_str is not None else 0,
        "start_turn_idx": int(extract_comment_prop("startTurnIdx", comment_str)),
        "komi": komi,
        "adv_komi": adv_komi,
        "handicap": int(extract_prop("HA", sgf_str)),
        "num_moves": len(semicolon_pattern.findall(sgf_str)) - 1,
        "ko_rule": extract_re(r"ko([A-Z]+)", rule_str),
        "score_rule": extract_re(r"score([A-Z]+)", rule_str),
        "tax_rule": extract_re(r"tax([A-Z]+)", rule_str),
        "sui_legal": extract_re(r"sui([0-9])", rule_str) == "1",
        "has_button": "button1" in rule_str,
        "whb": whb,
        "fpok": "fpok" in rule_str,
        "victim_color": "b" if b_name == "victim" else "w",
        "adv_color": adv_color,
        "win_color": win_color,
        "adv_samples": int(adv_samples_str) if adv_samples_str is not None else 0,
        "adv_minus_victim_score_wo_komi": adv_minus_victim_score - adv_komi,
        "init_turn_num": int(extract_comment_prop("initTurnNum", comment_str)),
        "used_initial_position": extract_comment_prop(
            "usedInitialPosition",
            comment_str,
        )
        == "1",
        "sgf_path": path,
        "sgf_line": line_number,
        "adv_name": adv_name,
        "gtype": extract_comment_prop("gtype", comment_str),
        "is_continuation": False,
    }

    if not fast_parse:
        # findall() is much slower than extracting a single regex
        num_b_pass = (
            len(num_b_pass_pattern.findall(sgf_str))
            + (
                len(
                    re.findall(
                        "B\\[tt]",
                        sgf_str,
                    ),
                )
                if board_size <= 19
                else 0
            ),
        )
        num_w_pass = (
            len(num_w_pass_pattern.findall(sgf_str))
            + (len(re.findall("W\\[tt]", sgf_str)) if board_size <= 19 else 0),
        )
        parsed_info["num_b_pass"] = num_b_pass
        parsed_info["num_w_pass"] = num_w_pass
        parsed_info["num_adv_pass"] = num_b_pass if adv_color == "b" else num_w_pass
        parsed_info["num_victim_pass"] = num_w_pass if adv_color == "b" else num_b_pass
        parsed_info["b_name"] = b_name
        parsed_info["w_name"] = w_name

    return parsed_info
