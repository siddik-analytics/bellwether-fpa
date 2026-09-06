"""Headless parity — criteria 5.6, 5.7 and 5.8.

Phase 4's criterion 4.25 said "deleting the COM stage leaves a complete, usable model" and passed
trivially, because the stage was empty. It stops being trivial the moment the stage does
something, so it is tested here rather than argued.

Two independent checks, because they fail differently:

- **pywin32 unresolvable.** Not merely uninstalled — actively unimportable, the way it is on
  Linux. A module-scope ``import win32com`` would pass a test that only checked it was absent
  from the environment, then fail in CI.
- **The package physically removed.** Catches an import that reaches ``bellwether.excel_stage``
  itself rather than the COM library underneath it.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import textwrap

import pytest

from bellwether.paths import REPO_ROOT

#: Refuse to import anything under these names, whatever is installed.
BLOCKER = textwrap.dedent(
    """
    import sys

    class Blocked:
        BANNED = ("win32com", "win32api", "pythoncom", "pywintypes", "win32")

        def find_module(self, name, path=None):
            return self if self._banned(name) else None

        def find_spec(self, name, path=None, target=None):
            if self._banned(name):
                raise ImportError(f"{name} is unresolvable in this environment")
            return None

        def _banned(self, name):
            root = name.split(".")[0]
            return root in self.BANNED

    sys.meta_path.insert(0, Blocked())
    """
).strip()


def _hash(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(code: str, cwd, env_extra=None) -> subprocess.CompletedProcess:
    import os

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=900,
    )


@pytest.fixture(scope="module")
def reference_workbook(tmp_path_factory):
    """A fresh headless build, as the thing parity is measured against.

    Deliberately not ``build/northlake-model.xlsx``: the Excel stage saves its Data Tables into
    that file, so the artifact on disk is the COM-modified one. Comparing against it would make
    this test fail for the wrong reason, or — worse — pass while comparing two mutated files.
    """
    from bellwether.data import generate
    from bellwether.workbook import model

    path = tmp_path_factory.mktemp("reference") / "northlake-model.xlsx"
    model.build(generate.generate(), path)
    return path


def test_the_build_runs_with_pywin32_unresolvable(tmp_path, reference_workbook) -> None:
    """5.6 — the Linux condition, reproduced on Windows.

    The reference workbook is rebuilt inside the subprocess and compared by hash, so this proves
    the headless path produces the *same* artifact rather than merely producing one.
    """
    expected = _hash(reference_workbook)
    code = BLOCKER + textwrap.dedent(
        f"""
            import hashlib, pathlib, sys
            try:
                import win32com  # noqa: F401
            except ImportError:
                pass
            else:
                raise SystemExit("win32com was importable; the blocker did not work")

            from bellwether.data import generate
            from bellwether.workbook import model
            out = pathlib.Path(r"{tmp_path}") / "headless.xlsx"
            model.build(generate.generate(), out)
            print(hashlib.sha256(out.read_bytes()).hexdigest())
            """
    )
    result = _run(code, REPO_ROOT)
    assert result.returncode == 0, result.stderr[-3000:]
    assert result.stdout.strip().splitlines()[-1] == expected, "headless build differs"


def test_the_build_runs_with_the_com_stage_deleted(tmp_path, reference_workbook) -> None:
    """5.6 — the stage is deletable, checked by deleting it."""
    tree = tmp_path / "repo"
    shutil.copytree(
        REPO_ROOT / "src",
        tree / "src",
        ignore=shutil.ignore_patterns("__pycache__", "excel_stage"),
    )
    assert not (tree / "src" / "bellwether" / "excel_stage").exists()

    code = textwrap.dedent(
        f"""
        import hashlib, pathlib, sys
        sys.path.insert(0, r"{tree / "src"}")
        import bellwether
        assert r"{tree}" in bellwether.__file__, bellwether.__file__

        from bellwether.data import generate
        from bellwether.workbook import model
        out = pathlib.Path(r"{tmp_path}") / "deleted.xlsx"
        model.build(generate.generate(), out)
        print(hashlib.sha256(out.read_bytes()).hexdigest())
        """
    )
    result = _run(code, tmp_path)
    assert result.returncode == 0, result.stderr[-3000:]
    assert result.stdout.strip().splitlines()[-1] == _hash(reference_workbook)


def test_nothing_outside_the_stage_imports_it() -> None:
    """5.7 — the import graph, asserted rather than trusted to discipline."""
    offenders = []
    for path in (REPO_ROOT / "src").rglob("*.py"):
        if "excel_stage" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) and "excel_stage" in stripped:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {stripped}")
    assert not offenders, offenders


def test_the_stage_imports_com_lazily() -> None:
    """5.6 again, at the source level: a module-scope import would break the Linux build.

    Checked separately from the subprocess test because this one names the file and line, and
    the subprocess test only says the build failed.
    """
    for name in ("com.py", "reconcile.py", "data_tables.py", "__main__.py"):
        path = REPO_ROOT / "src" / "bellwether" / "excel_stage" / name
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.startswith(("import ", "from ")):
                continue  # indented imports are the lazy ones, which is the point
            assert "win32" not in line and "pythoncom" not in line, f"{name}:{number} {line}"
