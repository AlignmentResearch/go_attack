"""Deletes old shuffleddata directories to clear up space."""

import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete old shuffleddata directories")
    parser.add_argument(
        "victimplay_dir",
        type=Path,
        help="Path in which which to recursively search for shuffleddata",
    )
    parser.add_argument(
        "--since-days",
        type=int,
        default=1,
        help="shuffledata not modified since this many days will be deleted",
    )
    args = parser.parse_args()
    victimplay_dir = args.victimplay_dir
    days = args.since_days

    # Find all shuffleddata files recursively.
    dirs_to_delete = []
    dirs_to_keep = []
    now = datetime.now()
    oldest_date_allowed = now - timedelta(days=days)
    for child_dir in victimplay_dir.rglob("shuffleddata/"):
        if child_dir.is_symlink():
            continue
        mod_time = datetime.fromtimestamp(child_dir.stat().st_mtime)
        if mod_time < oldest_date_allowed:
            dirs_to_delete.append(child_dir)
        else:
            dirs_to_keep.append(child_dir)

    # Confirm with user that the deletions look correct.
    print("The following shuffleddata directories will be deleted:")
    for file in dirs_to_delete:
        print(file)
    print("\nThe following shuffleddata directories will be kept:")
    for file in dirs_to_keep:
        print(file)
    confirm = input("Confirm file deletions (y/n): ")

    if confirm.lower().startswith("y"):
        for data_dir in dirs_to_delete:
            shutil.rmtree(data_dir)
    else:
        print("Deletions canceled")
