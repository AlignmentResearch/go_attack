#!/usr/bin/python3
import argparse
import json
import multiprocessing
import os
import time
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import numpy as np

# KataGo selfplay data.
SELFPLAY_DATA = [Path("/shared/katago-training-data/20220301-to-20220624/")]
# Number of rows in SELFPLAY_DATA.
SELFPLAY_NUM_ROWS = 125539529
# Victimplay data of cp505 playing against the cyclic adversary.
CYCLIC_DATA = [
    Path(
        "/shared/nas-data/k8/victimplay/ttseng-finetune-cp505-amcts-20230223-221152/selfplay"
    ),
    Path(
        "/shared/nas-data/k8/victimplay/ttseng-finetune-cp505-20230223-175823/selfplay"
    ),
]
CYCLIC_NUM_ROWS = 20073598


class TimeStuff(object):
    def __init__(self, taskstr):
        self.taskstr = taskstr

    def __enter__(self):
        print("Beginning: %s" % self.taskstr, flush=True)
        self.t0 = time.time()

    def __exit__(self, exception_type, exception_val, trace):
        self.t1 = time.time()
        print(
            "Finished: %s in %s seconds" % (self.taskstr, str(self.t1 - self.t0)),
            flush=True,
        )
        return False


def get_numpy_npz_headers(filename):
    with zipfile.ZipFile(filename) as z:
        wasbad = False
        numrows = 0
        npzheaders = {}
        for subfilename in z.namelist():
            npyfile = z.open(subfilename)
            try:
                version = np.lib.format.read_magic(npyfile)
            except ValueError:
                wasbad = True
                print(
                    "WARNING: bad file, skipping it: %s (bad array %s)"
                    % (filename, subfilename)
                )
            else:
                (shape, is_fortran, dtype) = np.lib.format._read_array_header(
                    npyfile, version
                )
                npzheaders[subfilename] = (shape, is_fortran, dtype)
        if wasbad:
            return None
        return npzheaders


def compute_num_rows(filename):
    try:
        npheaders = get_numpy_npz_headers(filename)
    except PermissionError:
        print("WARNING: No permissions for reading file: ", filename)
        return (filename, None)
    except zipfile.BadZipFile:
        print("WARNING: Bad zip file: ", filename)
        return (filename, None)
    if npheaders is None or len(npheaders) <= 0:
        print("WARNING: bad npz headers for file: ", filename)
        return (filename, None)
    (shape, is_fortran, dtype) = npheaders["binaryInputNCHWPacked"]
    num_rows = shape[0]
    return (filename, num_rows)


def get_files(
    dirs: Iterable[Path],
    max_rows: Optional[int] = None,
    write_rows_summary: bool = False,
) -> Tuple[List[Path], int]:
    """Get data files from `dirs` up until `max_rows` is reached."""
    all_files = []
    for d in dirs:
        dir_files = []
        summarized_files = set()
        unsummarized_files = []

        rows_summary_filename = d / "num_rows_summary.json"
        if rows_summary_filename.exists():
            print(f"Reading summary file {rows_summary_filename}")
            with open(rows_summary_filename) as f:
                dir_files = json.load(f)
            summarized_files = set([filename for filename, _, _ in dir_files])

        for (path, dirnames, filenames) in os.walk(d, followlinks=True):
            filenames = [
                os.path.join(path, filename)
                for filename in filenames
                if filename.endswith(".npz")
            ]
            filenames = [
                (filename, os.path.getmtime(filename)) for filename in filenames
            ]
            unsummarized_files.extend(
                [
                    (filename, mtime)
                    for filename, mtime in filenames
                    if filename not in summarized_files
                ]
            )

        with TimeStuff("Computing rows for unsummarized files"):
            print(f"Unsummarized files: {len(unsummarized_files)}")
            NUM_PROCESSES = 16
            with multiprocessing.Pool(NUM_PROCESSES) as pool:
                results = pool.map(
                    compute_num_rows, [filename for filename, _, in unsummarized_files]
                )
                results = dict(results)
                for info in unsummarized_files:
                    if len(info) < 3:
                        dir_files.append((info[0], info[1], results[info[0]]))

        if write_rows_summary:
            if len(unsummarized_files) == 0:
                print("No new files, skipping writing summary")
            print(f"Writing summary {rows_summary_filename}")
            with open(rows_summary_filename, "w") as f:
                json.dump(dir_files, f)

        all_files.extend(dir_files)

    with TimeStuff("Sorting"):
        all_files.sort(key=(lambda x: x[1]), reverse=True)

    desired_files = []
    num_rows_total = 0
    for filename, mtime, num_rows in all_files:  # pytype:disable=bad-unpacking
        if num_rows is None:
            print("WARNING: Skipping bad file: ", filename)
            continue
        if num_rows <= 0:
            continue
        if max_rows is not None and max_rows < num_rows_total + num_rows:
            break
        num_rows_total += num_rows
        desired_files.append(Path(filename))

    return desired_files, num_rows_total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gets a mix of cp505 selfplay and victimplay data for adversarially training cp505."
    )
    parser.add_argument(
        "-out-dir",
        type=Path,
        required=True,
        help="The output directory for the mix of data",
    )
    parser.add_argument(
        "-selfplay-proportion",
        type=float,
        required=True,
        help="The percentage of data rows to be selfplay games",
    )
    parser.add_argument(
        "-write-rows-summary",
        action="store_true",
        help="Writes a data summary file caching the number of data rows per file so that this script can execute quicker in subsequent runs",
    )

    args = parser.parse_args()
    out_dir = args.out_dir
    selfplay_proportion = args.selfplay_proportion
    write_rows_summary = args.write_rows_summary

    assert 0 < selfplay_proportion < 1
    cyclic_proportion = 1 - selfplay_proportion
    desired_selfplay_num_rows = min(
        SELFPLAY_NUM_ROWS, CYCLIC_NUM_ROWS / cyclic_proportion - CYCLIC_NUM_ROWS
    )
    desired_cyclic_num_rows = min(
        CYCLIC_NUM_ROWS, SELFPLAY_NUM_ROWS / selfplay_proportion - SELFPLAY_NUM_ROWS
    )
    assert np.isclose(
        desired_selfplay_num_rows
        / (desired_selfplay_num_rows + desired_cyclic_num_rows),
        selfplay_proportion,
    )

    for desired_num_rows, data_dirs, label in [
        (desired_cyclic_num_rows, CYCLIC_DATA, "cyclic"),
        (desired_selfplay_num_rows, SELFPLAY_DATA, "selfplay"),
    ]:
        files, num_rows = get_files(
            data_dirs, desired_num_rows, write_rows_summary=write_rows_summary
        )
        num_rows_percent_error = (desired_num_rows - num_rows) / desired_num_rows * 100
        print(
            f"{label}: wanted {desired_num_rows}, got {num_rows} ({num_rows_percent_error}% error)"
        )
        for f in files:
            # Joining two absolute paths `out_dir` and `f`:
            # https://stackoverflow.com/questions/50846049/join-two-absolute-paths
            symlink_dst = out_dir / f.relative_to(f.anchor)
            if symlink_dst.exists():
                continue
            symlink_dst.parent.mkdir(parents=True, exist_ok=True)
            symlink_dst.symlink_to(f)
