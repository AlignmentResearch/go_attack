import argparse
import os
from pathlib import Path
import subprocess

import sgfmill.sgf


def get_sgf_score(sgf_file: Path):
    """Get score listed in SGF file."""
    with open(sgf_file) as f:
        return sgfmill.sgf.Sgf_game.from_string(f.read()).get_root().get("RE")


def get_sgf_files_in_path(path: Path):
    """Recursively get all SGF files in the path."""
    if path.suffix in [".sgf", ".sgfs"]:
        yield str(path)
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            f_path = Path(os.path.join(dirpath, f))
            if f_path.suffix in [".sgf", ".sgfs"]:
                yield str(f_path)


def main():
    parser = argparse.ArgumentParser(
        description="Rescores SGFs using KataGo's Tromp-Taylor scoring."
    )
    parser.add_argument(
        "sgf_path",
        type=Path,
        help=(
            "Path to directory (to be searched recursively) containing input "
            "SGFs. The SGF files are expected to contain one SGF per file."
        ),
    )
    parser.add_argument(
        "--katago_command",
        type=str,
        help="Command with which to run KataGo in GTP mode",
    )
    # parser.add_argument(
    #     "-o", "--output", type=Path, help="Path to directory at which to output SGFs"
    # )

    args = parser.parse_args()
    if args.katago_command is None:
        args.katago_command = (
            "docker run --gpus '\"device=0\"' "
            f"-v {args.sgf_path}:{args.sgf_path} -i "
            "humancompatibleai/goattack:cpp "
            "/engines/KataGo-raw/cpp/katago gtp "
            "-config /engines/KataGo-raw/cpp/configs/gtp_example.cfg "
            "-model /dev/null"
        )

    proc = subprocess.Popen(
        args.katago_command,
        bufsize=0,
        shell=True,
        stderr=open("/tmp/score-with-katago.stderr", "w"),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    to_engine = proc.stdin
    from_engine = proc.stdout

    def write_to_engine(message):
        to_engine.write(message.encode("ascii"))

        output = ""
        found_output_start = False
        for i, line in enumerate(from_engine):
            line = line.decode("ascii")

            if found_output_start and line.strip() == "":
                # Blank line signals the end of a response
                break

            if not found_output_start and line[0] == "=":
                found_output_start = True
                output += line[1:]
            else:
                output += line
        return output.lstrip().strip(), found_output_start

    for path in get_sgf_files_in_path(args.sgf_path):
        _, success = write_to_engine(f"loadsgf {path}\n")
        assert success
        _, success = write_to_engine("kata-set-rules Tromp-Taylor\n")
        assert success
        katago_score, success = write_to_engine("final_score\n")

        print(f"KataGo score: {katago_score}, orig score: {get_sgf_score(path)}")


if __name__ == "__main__":
    main()
