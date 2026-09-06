"""Phase 0 acceptance criteria, as assertions.

Every guardrail this phase exists to establish is checked here. An untested guardrail is not
a guardrail — and the failure it protects against (a binary in the history of a public repo)
is permanent.

Criteria are numbered to match ``docs/phases/phase-00-spec.md``.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from bellwether.paths import BUILD_DIR, DATA_DIR, REPO_ROOT

#: Filenames the repo must never accept. Real names, not sanitised examples: `~$` files are
#: the ones that actually appear, mid-session, while Excel holds the workbook open.
FORBIDDEN_FILES = [
    "build/bellwether-model.xlsx",
    "model.xlsm",
    "legacy/plan.xls",
    "powerbi/bellwether.pbix",
    "powerbi/template.pbit",
    "build/board-pack.pdf",
    "~$bellwether-model.xlsx",
    "docs/~$notes.docx",
]

#: Files that must pass unobstructed. A guardrail that blocks ordinary work gets disabled.
PERMITTED_FILES = [
    "src/bellwether/transform/statements.py",
    "powerbi/bellwether.SemanticModel/definition/model.tmdl",
    "powerbi/bellwether.Report/report.json",
    "docs/adr/0001-beginning-balance-interest.md",
    "tests/test_scaffold.py",
    "data/README.md",
]


def _artifact_hook_pattern() -> re.Pattern[str]:
    """The `files:` regex from the local binary-rejection pre-commit hook."""
    config = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    local = next(r for r in config["repos"] if r["repo"] == "local")
    hook = next(h for h in local["hooks"] if h["id"] == "no-binary-artifacts")
    assert hook["language"] == "fail", "the hook must fail on match, not merely report"
    return re.compile(hook["files"])


# --- 0.1 -------------------------------------------------------------------------------


def test_headless_build_exits_zero() -> None:
    """`python -m bellwether.build` succeeds without Excel.

    Run as a subprocess deliberately: importing ``main`` would not catch a broken
    ``__main__`` guard or a packaging error that only shows up via ``-m``.
    """
    result = subprocess.run(
        [sys.executable, "-m", "bellwether.build"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_build_writes_only_into_ignored_directories() -> None:
    """0.5 — the working tree stays clean after a build.

    The build may create output directories; it must not create anything git would report.
    """
    subprocess.run(
        [sys.executable, "-m", "bellwether.build"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    stray = [
        line for line in status.stdout.splitlines() if line[3:].startswith(("data/", "build/"))
    ]
    assert stray == [], f"build output is visible to git: {stray}"


# --- 0.4 -------------------------------------------------------------------------------


@pytest.mark.parametrize("path", FORBIDDEN_FILES)
def test_pre_commit_hook_rejects_artifact(path: str) -> None:
    assert _artifact_hook_pattern().search(path), f"{path} would reach a commit"


@pytest.mark.parametrize("path", PERMITTED_FILES)
def test_pre_commit_hook_allows_source(path: str) -> None:
    assert not _artifact_hook_pattern().search(path), f"{path} is blocked but should not be"


@pytest.mark.parametrize("path", FORBIDDEN_FILES)
def test_gitignore_covers_artifact(path: str) -> None:
    """.gitignore is the first line of defence; the hook is the second.

    Asked of git itself rather than by re-reading the file, so the answer accounts for
    negations and ordering exactly as a real `git add` would.
    """
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", path],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    assert result.returncode == 0, f"{path} is not gitignored"


@pytest.mark.parametrize("path", ["data/", "build/", ".venv/", ".env"])
def test_gitignore_covers_generated_directories(path: str) -> None:
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", path],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    assert result.returncode == 0, f"{path} is not gitignored"


# --- test configuration itself ---------------------------------------------------------


def test_requires_excel_marker_is_registered_and_strict() -> None:
    """An unregistered marker under a non-strict config skips silently.

    That failure mode is invisible: the Excel reconciliation suite would report green while
    running nothing at all.
    """
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pytest_config = config["tool"]["pytest"]["ini_options"]

    assert "--strict-markers" in pytest_config["addopts"]
    assert any(m.startswith("requires_excel:") for m in pytest_config["markers"])


# --- layout ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "CLAUDE.md",
        "docs/charter.md",
        "docs/architecture.md",
        "docs/adr/0001-beginning-balance-interest.md",
        "docs/phases/phase-00-spec.md",
        ".claude/rules/excel-com.md",
        ".github/workflows/ci.yml",
    ],
)
def test_documented_file_exists(relative: str) -> None:
    assert (REPO_ROOT / relative).is_file(), f"{relative} is referenced but missing"


def test_output_directories_are_outside_the_source_tree() -> None:
    """Generated output must never land under `src/`, where it would be packaged."""
    src = REPO_ROOT / "src"
    for directory in (DATA_DIR, BUILD_DIR):
        assert src not in Path(directory).parents
