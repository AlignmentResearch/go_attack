"""Rescores SGFs using KataGo's Tromp-Taylor scoring.

KataGo scoring clears out opposite-color stones within pass-alive groups. For
consistency throughout experiments, we should use KataGo scoring everywhere
(including in experiments where otherwise KataGo isn't involved at all like
baseline attacks vs. ELF).
"""
import argparse
import getpass
import os
import shutil
import subprocess
from pathlib import Path

import sgfmill.sgf


def get_sgfs_in_file(sgf_file: Path):
    """Get all SGFs in a file."""
    if sgf_file.suffix == ".sgf":
        # Assume entire file is one SGF.
        with open(sgf_file) as f:
            yield sgfmill.sgf.Sgf_game.from_string(f.read())
    elif sgf_file.suffix == ".sgfs":
        # Assume each line in the file is an SGF.
        with open(sgf_file) as f:
            for line in f:
                yield sgfmill.sgf.Sgf_game.from_string(line)


def get_sgfs_in_path(path: Path):
    """Recursively get all SGFs in a path."""
    yield from get_sgfs_in_file(path)
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            child_path = Path(os.path.join(dirpath, f))
            yield from get_sgfs_in_file(child_path)


def score_str_to_white_score(score_str: str) -> float:
    """Convert a score string (e.g., B+35.5) to a numerical score for white."""
    winner, score = score_str.split("+")
    score = float(score)
    if winner == "B":
        score = -score
    return score


def get_white_score(game: sgfmill.sgf.Sgf_game) -> float:
    """Get score for white from a game."""
    score_str = game.get_root().get("RE")
    return score_str_to_white_score(score_str)


def main():
    """Entrypoint for script."""
    parser = argparse.ArgumentParser(
        description="Rescores SGFs using KataGo's Tromp-Taylor scoring.",
    )
    parser.add_argument(
        "sgf_path",
        type=Path,
        help="Path to directory (to be searched recursively) with input SGFs",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Path to file to write output SGFs",
        default=os.devnull,
    )
    tmp_dir = Path(f"/tmp/score-with-katago-{getpass.getuser()}")
    os.makedirs(tmp_dir, exist_ok=True)
    parser.add_argument(
        "-e",
        "--executable",
        type=str,
        help="Path to KataGo executable",
        default=(
            f"docker run -i -v {tmp_dir}:{tmp_dir} "
            "humancompatibleai/goattack:cpp /engines/KataGo-raw/cpp/katago"
        )
    )
    args = parser.parse_args()
    if args.output.is_file():
        raise ValueError(f"Output file already exists: {args.output}")

    katago_command = (
        f"{args.executable} gtp "
        "-config /engines/KataGo-raw/cpp/configs/gtp_example.cfg "
        "-model /dev/null"
    )
    proc = subprocess.Popen(
        katago_command,
        bufsize=0,
        shell=True,
        stderr=open(tmp_dir / "stderr.log", "w"),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    to_engine = proc.stdin
    from_engine = proc.stdout
    assert to_engine is not None

    def send_command(message, assert_success=True):
        to_engine.write(f"{message}\n".encode("ascii"))
        output = ""
        found_output_start = False
        success = False
        for i, line in enumerate(from_engine):
            line = line.decode("ascii")

            if found_output_start and line.strip() == "":
                # Blank line signals the end of a response.
                break

            if not found_output_start:
                if line[0] == "?":
                    # Error response, no success.
                    found_output_start = True
                    output += line[1:]
                elif line[0] == "=":
                    success = True
                    found_output_start = True
                    output += line[1:]
            else:
                output += line
        if assert_success:
            assert success
        return output.lstrip().strip()

    num_games = 0
    num_flipped_games = 0
    squared_error_sum = 0
    tmp_sgf_path = tmp_dir / "game.sgf"
    with open(args.output, "wb") as output_file:
        for sgf in get_sgfs_in_path(args.sgf_path):
            try:
                original_score = get_white_score(sgf)
            except KeyError:
                print("Skipping game due to no result")
                continue

            with open(tmp_sgf_path, "wb") as katago_input_sgf_file:
                katago_input_sgf_file.write(sgf.serialise())
            send_command(f"loadsgf {tmp_sgf_path}")
            send_command("kata-set-rules Tromp-Taylor")
            # We need to make sure KataGo thinks the game has ended or else it may
            # estimate the score using its model (which in this case is /dev/null, a
            # random model).
            send_command("play b pass")
            send_command("play w pass")
            katago_score_str = send_command("final_score")

            katago_score = score_str_to_white_score(katago_score_str)
            squared_error_sum += (katago_score - original_score) ** 2
            num_games += 1
            if katago_score * original_score < 0:
                num_flipped_games += 1

            sgf.get_root().set("RE", katago_score_str)
            output_file.write(sgf.serialise(wrap=None))
    if num_games > 0:
        print(f"Games that changed winners: {num_flipped_games}/{num_games}")
        print(f"Mean squared error: {squared_error_sum / num_games}")
    else:
        print("No games found.")
    shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    main()
