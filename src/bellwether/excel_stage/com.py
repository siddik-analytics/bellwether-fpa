"""COM primitives — the only module in the project that talks to Excel.

Windows-only and **additive only**. Everything here opens a workbook the headless build already
produced, asks Excel to recalculate it, and reads values back. Nothing here writes a financial
value; if a number appeared here that the oracle did not compute, that would be a defect
regardless of whether the number is right.

``pywin32`` is imported **inside** the functions rather than at module scope, so importing
``bellwether.excel_stage`` on Linux succeeds and fails only if someone actually calls COM.
Criterion 5.6 builds with the package unimportable to prove the headless path never does.
"""

from __future__ import annotations

import contextlib
import functools
import pathlib
import re
import time
from dataclasses import dataclass

#: ``xlCalculationManual`` / ``xlCalculationAutomatic``.
CALCULATION_MANUAL = -4135
CALCULATION_AUTOMATIC = -4105

#: A cell reference on a worksheet, as the reconciliation reports it.
CELL = re.compile(r"^([A-Z]+)(\d+)$")


class ExcelUnavailable(RuntimeError):
    """Excel or pywin32 is not present. Every caller of this module is Windows-only."""


@dataclass(frozen=True)
class Difference:
    """One cell where Excel and the oracle disagree."""

    sheet: str
    cell: str
    formula: str
    cached: float
    recalculated: float

    @property
    def delta(self) -> float:
        return abs(self.cached - self.recalculated)

    def __str__(self) -> str:
        return (
            f"{self.sheet}!{self.cell}  {self.formula}  "
            f"cached {self.cached:,.4f}  recalculated {self.recalculated:,.4f}  "
            f"delta {self.delta:,.4f}"
        )


def _client():
    try:
        # Lazy by design - see the module docstring and criterion 5.6.
        import win32com.client
    except ImportError as exc:  # pragma: no cover - Linux path
        raise ExcelUnavailable("pywin32 is not installed; the Excel stage is Windows-only") from exc
    return win32com.client


def available() -> bool:
    """Whether this machine can run the Excel stage at all."""
    try:
        client = _client()
    except ExcelUnavailable:
        return False
    try:
        application = client.Dispatch("Excel.Application")
    except Exception:  # pragma: no cover - no Excel installed
        return False
    with contextlib.suppress(Exception):
        application.Quit()
    return True


#: "Call was rejected by callee" and friends. Excel raises these under load and they mean
#: nothing; treating the first one as a real failure makes the stage flaky for no reason.
TRANSIENT = ("call was rejected by callee", "server is busy", "rpc_e_", "0x8001010a")


def retry(attempts: int = 5, delay: float = 0.4):
    """Retry transient COM failures with backoff, and only transient ones.

    A blanket retry would paper over a genuine error by trying it five times; the message is
    matched so a real failure still surfaces on the first attempt.
    """

    def decorate(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            for attempt in range(attempts):
                try:
                    return function(*args, **kwargs)
                except Exception as exc:
                    text = str(exc).lower()
                    if attempt == attempts - 1 or not any(t in text for t in TRANSIENT):
                        raise
                    time.sleep(delay * (2**attempt))
            raise AssertionError("unreachable")

        return wrapper

    return decorate


@contextlib.contextmanager
def application(visible: bool = False):
    """A dedicated, isolated Excel instance, torn down even if the body raises.

    ``DispatchEx`` rather than ``Dispatch`` so this never attaches to an Excel the user already
    has open — automating someone's live session is how a stage like this destroys work.

    Add-ins and ``PERSONAL.XLSB`` are suppressed: an inherited add-in makes automation slow and
    unpredictable in ways that are painful to diagnose, and the workbook under test must behave
    the same on every machine.

    A leaked EXCEL.EXE holds a file lock that makes the next build fail with an error that looks
    nothing like its cause, so the teardown is not optional.
    """
    client = _client()
    app = client.DispatchEx("Excel.Application")
    app.Visible = visible
    app.DisplayAlerts = False
    app.AskToUpdateLinks = False
    app.EnableEvents = False
    app.ScreenUpdating = False
    for add_in in list(app.AddIns):
        with contextlib.suppress(Exception):
            if add_in.Installed:
                add_in.Installed = False
    try:
        yield app
    finally:
        with contextlib.suppress(Exception):
            app.Quit()
        del app


@retry()
def _open(app, path: pathlib.Path):
    """Open by absolute path. COM does not resolve paths against the Python working directory,
    and silently writes to the wrong place when handed a relative one."""
    return app.Workbooks.Open(str(pathlib.Path(path).resolve()))


@contextlib.contextmanager
def workbook(path: pathlib.Path, visible: bool = False):
    """Open a workbook read-write, always closing it without saving unless asked."""
    with application(visible) as app:
        book = _open(app, path)
        try:
            yield app, book
        finally:
            with contextlib.suppress(Exception):
                book.Close(SaveChanges=False)


def opened_without_repair(path: pathlib.Path) -> tuple[bool, str]:
    """Criterion 5.4 — did Excel have to repair the file to open it?

    A repaired file is one Excel rewrote because the original was structurally invalid. Every
    value could be correct and the deliverable would still be unusable, because the first thing
    a reader sees is a dialog saying the file is damaged.

    Detection is ``Workbook.Saved`` immediately after opening. Excel marks a workbook dirty the
    moment it has to convert or repair anything, and leaves an untouched file clean — so a
    workbook that arrives already needing a save was rewritten on the way in. This is checked
    rather than trusted to the alert dialog, which ``DisplayAlerts = False`` suppresses.
    """
    with application() as app:
        book = _open(app, path)
        try:
            clean = bool(book.Saved)
            message = "" if clean else "Excel modified the workbook while opening it"
            return clean, message
        finally:
            with contextlib.suppress(Exception):
                book.Close(SaveChanges=False)


def recalculate(book) -> None:
    """Force a genuine full rebuild, not a dependency-graph refresh.

    ``CalculateFullRebuild`` discards the dependency tree and every cached result, which is the
    only mode that actually re-evaluates a formula whose cached value was written by something
    other than Excel. ``Calculate`` would happily return the cached values this test exists to
    check.
    """
    book.Application.Calculation = CALCULATION_MANUAL
    book.Application.CalculateFullRebuild()
    while book.Application.CalculationState != 0:  # xlDone
        pass


def formula_cells(book) -> list[tuple[str, str, str, float]]:
    """Every formula cell in the workbook: sheet, cell, formula, current value.

    Read in one bulk ``UsedRange`` fetch per sheet. Cell-by-cell COM round trips take minutes on
    a workbook this size; two array reads take under a second.
    """
    out: list[tuple[str, str, str, float]] = []
    for sheet in book.Worksheets:
        used = sheet.UsedRange
        if used is None:
            continue
        formulas = used.Formula
        values = used.Value2
        if not isinstance(formulas, tuple):
            formulas, values = ((formulas,),), ((values,),)
        first_row, first_col = used.Row, used.Column
        for r, row in enumerate(formulas):
            for c, formula in enumerate(row):
                if not isinstance(formula, str) or not formula.startswith("="):
                    continue
                value = values[r][c]
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    continue
                reference = f"{_column_letter(first_col + c)}{first_row + r}"
                out.append((sheet.Name, reference, formula, float(value)))
    return out


def _column_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters
