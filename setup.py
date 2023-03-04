"""Setup for go_attack: research code attacking Go AI systems."""

from setuptools import find_packages, setup

import src.go_attack  # pytype: disable=import-error

TESTS_REQUIRE = [
    "black[jupyter]",
    "coverage",
    "codecov",
    "codespell",
    "darglint",
    "flake8",
    "flake8-blind-except",
    "flake8-builtins",
    "flake8-commas",
    "flake8-debugger",
    "flake8-docstrings",
    "flake8-isort",
    "ipykernel",
    "jupyter",
    # remove pin once https://github.com/jupyter/jupyter_client/issues/637 fixed
    "jupyter-client<7.0",
    "pytest",
    "pytest-cov",
    "pytest-notebook",
    "pytest-xdist",
    "pytype",
]


def get_readme() -> str:
    """Retrieve content from README."""
    with open("README.md", "r") as f:
        return f.read()


setup(
    name="go_attack",
    version=src.go_attack.__version__,
    description="Research code attacking Go AI systems",
    long_description=get_readme(),
    long_description_content_type="text/markdown",
    author="FAR AI et al",
    python_requires=">=3.8.0",
    packages=find_packages("src"),
    package_dir={"": "src"},
    package_data={"go_attack": ["py.typed"]},
    install_requires=[
        "docker",
        "matplotlib",
        "numpy",
        "pandas",
        "pynvml",
        "scipy",
        "seaborn",
        "simple-parsing",
        "sgfmill",
        "tqdm",
    ],
    tests_require=TESTS_REQUIRE,
    extras_require={
        # recommended packages for development
        "dev": [
            "docker-compose",
            "gpustat",
            "ipywidgets",
            "jupyterlab",
            "pre-commit",
            # for convenience
            *TESTS_REQUIRE,
        ],
        # Suggest using the compose/python/Dockerfile for KataGo experiments.
        # But this will install minimal set of dependencies for development
        # using that codebase.
        "katago": [
            "psutil",
            "scipy",
            "tensorflow-gpu==1.15.5",
        ],
        "test": TESTS_REQUIRE,
    },
    url="https://github.com/AlignmentResearch/go_attack",
    license="MIT",
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)
