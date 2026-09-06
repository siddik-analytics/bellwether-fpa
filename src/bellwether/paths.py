"""Canonical filesystem locations, resolved absolutely.

Absolute paths are not a stylistic preference here: the Excel/COM stage does not resolve
relative paths against the Python working directory, and silently writes to the wrong place
when handed one. Everything in the project takes its paths from this module.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Generated synthetic data. Gitignored — regenerated from a seed, never committed.
DATA_DIR = REPO_ROOT / "data"

#: Build artifacts: workbook, board pack PDF, PNG exports. Gitignored outside release tags.
BUILD_DIR = REPO_ROOT / "build"

#: CSV samples of every generated table. Unlike DATA_DIR these are **committed**: they are the
#: only view of the dataset available to someone reading the repository on GitHub rather than
#: running it, and half this project's audience does exactly that.
SAMPLES_DIR = REPO_ROOT / "samples"

DOCS_DIR = REPO_ROOT / "docs"
POWERBI_DIR = REPO_ROOT / "powerbi"


def ensure_output_dirs() -> None:
    """Create the generated-output directories if they do not yet exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
