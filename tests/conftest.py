"""Shared fixtures.

``requires_excel`` is registered in ``pyproject.toml`` rather than here, so that
``--strict-markers`` rejects a typo'd marker instead of silently skipping the test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bellwether.paths import REPO_ROOT


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT
