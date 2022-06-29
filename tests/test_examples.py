"""Smoke tests for notebooks/*."""

import pathlib
from typing import Iterable, Sequence

import pytest
from pytest_notebook import execution, notebook


def _paths_to_strs(x: Iterable[pathlib.Path]) -> Sequence[str]:
    """Convert Path to str for nice Pytest `parameterized` logs.

    For example, if we use Path, we get something inscrutable like
    test_run_example_sh_scripts[sh_path0] rather than seeing the actual path name.

    Args:
        x: The paths to convert.

    Returns:
        A sequence of the same length as `x`, with each element the string
        representation of the corresponding path in `x`.
    """
    return [str(path) for path in x]


THIS_DIR = pathlib.Path(__file__).absolute().parent
NOTEBOOKS_DIR = THIS_DIR / ".." / "notebooks"
NB_PATHS = _paths_to_strs(NOTEBOOKS_DIR.glob("*.ipynb"))


@pytest.mark.parametrize("nb_path", NB_PATHS)
def test_run_example_notebooks(nb_path) -> None:
    """Smoke test ensuring that example notebooks run without error.

    The `pytest_notebook` package also includes regression test functionality against
    saved notebook outputs, if we want to check that later.

    Args:
        nb_path: Path to the notebook to test.
    """
    nb = notebook.load_notebook(nb_path)
    result = execution.execute_notebook(nb, cwd=NOTEBOOKS_DIR, timeout=120)
    assert result.exec_error is None
