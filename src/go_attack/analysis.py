"""Utilities for loading and manipulating KataGo analyses."""

import re
from pathlib import Path
from typing import Union

import pandas as pd


def load_analysis(path: Union[Path, str]) -> pd.DataFrame:
    """Loads a newline-delimited file of KataGo analyses into a DataFrame."""
    # space-delimited key-value pairs, where keys start with lowercase letters
    # and are at least 3 characters long.
    parser = re.compile(r"([a-z][a-zA-Z]{2,}) ([A-Z0-9-.]+)")
    return pd.concat(
        [
            pd.DataFrame(
                [
                    {k: maybe_to_float(v) for k, v in parser.findall(move)}
                    for move in line.split("info ")
                    if move
                ],
            ).assign(turn=i)
            for i, line in enumerate(open(path).readlines())
            if len(line) > 1  # Skip empty / newlines
        ],
    )


def maybe_to_float(s: str) -> Union[float, str]:
    """Converts a string to a float if possible."""
    try:
        return float(s)
    except ValueError:
        return s
