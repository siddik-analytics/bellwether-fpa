"""The carried phase 4 criteria — 5.1 to 5.5 and 5.9. Local Windows only.

`.claude/rules/excel-com.md` calls the reconciliation the strongest single artifact in the repo,
and it is the reason the workbook is built the way it is. Every test here is
``requires_excel``: CI skips them, which is exactly why the headless suite has to stand on its
own and why `tests/test_headless_parity.py` exists.
"""

from __future__ import annotations

import pathlib

import pytest

from bellwether.data import generate
from bellwether.excel_stage import com, data_tables, reconcile
from bellwether.workbook import model

pytestmark = pytest.mark.requires_excel


@pytest.fixture(scope="module")
def workbook(tmp_path_factory) -> pathlib.Path:
    """A private copy, so a test that saves cannot disturb the build artifact."""
    if not com.available():
        pytest.skip("Excel is not available on this machine")
    path = tmp_path_factory.mktemp("excel") / "northlake-model.xlsx"
    model.build(generate.generate(), path)
    return path


@pytest.fixture(scope="module")
def ranges(tmp_path_factory) -> dict:
    path = tmp_path_factory.mktemp("ranges") / "northlake-model.xlsx"
    return model.build(generate.generate(), path)["sensitivity_ranges"]


# --- 5.1 the reconciliation ------------------------------------------------------------------


def test_excel_reproduces_every_formula_within_a_cent(workbook) -> None:
    """5.1 — every formula cell, not a sample and not the totals.

    The failure this catches is a formula that is subtly wrong while its cached value is right.
    That is invisible in an aggregate, because the aggregate is built from the cached values.
    """
    report = reconcile.reconcile(workbook)
    assert report["compared"] > 1_800, report["compared"]
    assert not report["missing"], report["missing"][:5]
    assert not report["differences"], "\n" + reconcile.format_report(report, limit=20)


def test_the_reconciliation_can_actually_fail(tmp_path) -> None:
    """The negative control, and it has already earned its place.

    An earlier version of the harness read values through COM before and after recalculating.
    Excel evaluates formulas as it opens a workbook, so the "before" read was already Excel's
    own answer and the comparison was a value against itself — it reported zero differences on
    this very workbook. A reconciliation nobody has seen fail is not evidence of agreement.
    """
    import xlsxwriter

    path = tmp_path / "control.xlsx"
    book = xlsxwriter.Workbook(str(path))
    sheet = book.add_worksheet("Control")
    sheet.write_number(0, 0, 100.0)
    sheet.write_number(1, 0, 42.0)
    sheet.write_formula(2, 0, "=A1+A2", None, 142.0)
    sheet.write_formula(3, 0, "=A1+A2", None, 999.0)  # the planted lie
    sheet.write_formula(4, 0, "=A1*A2", None, 4200.0)
    book.close()

    report = reconcile.reconcile(path)
    assert len(report["differences"]) == 1, report["differences"]
    difference = report["differences"][0]
    assert difference.cell == "A4"
    assert abs(difference.recalculated - 142.0) < 0.01
    assert abs(difference.delta - 857.0) < 0.01


def test_cached_values_are_read_from_the_file_not_from_excel(workbook) -> None:
    """The property the negative control protects, asserted directly."""
    cached = reconcile.cached_values(workbook)
    assert len(cached) > 1_800
    assert ("P&L", "B6") in cached, "sheet names must be unescaped: workbook.xml says P&amp;L"


# --- 5.2 and 5.3 the Data Tables --------------------------------------------------------------


def test_data_tables_are_attached_and_still_agree(tmp_path, ranges) -> None:
    """5.2 and 5.3 — the sharper case, because a Data Table hands Excel a range to fill in."""
    path = tmp_path / "tables.xlsx"
    model.build(generate.generate(), path)
    report = data_tables.apply(path, ranges)

    assert report["all_are_tables"], "the ranges are still constants, not Data Tables"
    assert len(report["attached"]) == len(ranges)
    assert report["compared"] == sum(len(spec["values"]) for spec in ranges.values())
    assert not report["differences"], [str(d) for d in report["differences"]]


def test_attaching_data_tables_twice_is_a_no_op(tmp_path, ranges) -> None:
    """5.9 — the stage is idempotent. Re-attaching over a live array formula corrupts it."""
    path = tmp_path / "twice.xlsx"
    model.build(generate.generate(), path)

    first = data_tables.apply(path, ranges)
    second = data_tables.apply(path, ranges)

    assert len(first["attached"]) == len(ranges)
    assert second["attached"] == [], second["attached"]
    assert sorted(second["already_attached"]) == sorted(ranges)
    assert not second["differences"]


# --- 5.4 the file is not repaired --------------------------------------------------------------


def test_the_workbook_opens_without_a_repair_warning(workbook) -> None:
    """5.4 — every value could be right and the deliverable still unusable."""
    clean, message = com.opened_without_repair(workbook)
    assert clean, message


def test_a_workbook_survives_the_full_stage_and_reopens_clean(tmp_path, ranges) -> None:
    """The end state a reader actually receives: recalculated, tables attached, saved."""
    path = tmp_path / "packaged.xlsx"
    model.build(generate.generate(), path)
    data_tables.apply(path, ranges)

    clean, message = com.opened_without_repair(path)
    assert clean, message
    report = reconcile.reconcile(path)
    assert not report["differences"], "\n" + reconcile.format_report(report)


# --- 5.5 the stage originates nothing ----------------------------------------------------------


def test_the_stage_never_writes_a_financial_value() -> None:
    """5.5 — the boundary, asserted over the source rather than trusted.

    The stage is allowed to write exactly one kind of thing: a Data Table, which Excel fills in
    from a formula and inputs the oracle produced. Any other assignment into a cell would be
    this stage originating a figure.
    """
    from bellwether.paths import REPO_ROOT

    stage = REPO_ROOT / "src" / "bellwether" / "excel_stage"
    forbidden = (".Value =", ".Value2 =", ".Formula =", ".FormulaR1C1 =", ".Cells(")
    offenders = []
    for path in stage.rglob("*.py"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip().startswith("#"):
                continue
            for token in forbidden:
                if token in line:
                    offenders.append(f"{path.name}:{number} {line.strip()}")
    assert not offenders, offenders
