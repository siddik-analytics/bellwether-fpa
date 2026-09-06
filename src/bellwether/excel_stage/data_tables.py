"""Native Excel Data Tables over the oracle's sensitivity grids — criteria 5.2 and 5.3.

The only thing xlsxwriter genuinely cannot produce. A Data Table is a multi-cell array formula
Excel maintains itself: change the input cell and the whole column recomputes. That is the one
piece of interactivity a static workbook cannot fake, and it is why the COM stage exists at all.

It is also the sharpest test of the oracle rule. Attaching a Data Table hands Excel the job of
filling in a range of numbers — so after it is attached and the book recalculates, the values
must still equal what the oracle computed. Anything else is Excel quietly taking ownership of a
figure.
"""

from __future__ import annotations

import pathlib

from bellwether.excel_stage import com

TOLERANCE = 0.01


def attach(book, ranges: dict[str, dict]) -> list[str]:
    """Lay a one-variable Data Table over each grid. Returns the ranges converted."""
    attached = []
    for name, spec in ranges.items():
        sheet = book.Worksheets(spec["sheet"])
        table_range = sheet.Range(spec["table_range"])
        column_input = sheet.Range(spec["input_cell"])
        # Positional, not ColumnInput=. Range.Table takes (RowInput, ColumnInput), and pywin32's
        # late binding routes the keyword to the first parameter regardless of its name: the
        # keyword form raises "Input cell reference is not valid", and if it did not it would
        # build a row-oriented table that returns the inputs unchanged. Both were observed.
        table_range.Table(None, column_input)
        attached.append(f"{name} over {spec['sheet']}!{spec['table_range']}")
    return attached


def verify(book, ranges: dict[str, dict], tolerance: float = TOLERANCE) -> dict:
    """Criterion 5.3 — the live table still says what the oracle said.

    Read back the column Excel now maintains and compare it, row by row, with the grid the
    oracle produced. A Data Table that disagrees is the failure mode this whole stage is
    supposed to make impossible.
    """
    differences = []
    compared = 0
    for name, spec in ranges.items():
        sheet = book.Worksheets(spec["sheet"])
        first = spec["first_value_row"]
        for offset, expected in enumerate(spec["values"]):
            cell = f"B{first + offset}"
            actual = sheet.Range(cell).Value2
            compared += 1
            if actual is None or abs(float(actual) - expected) > tolerance:
                differences.append(
                    com.Difference(
                        sheet=spec["sheet"],
                        cell=f"{name} {cell}",
                        formula="{=TABLE(,input)}",
                        cached=expected,
                        recalculated=float(actual) if actual is not None else float("nan"),
                    )
                )
    return {
        "compared": compared,
        "differences": differences,
        "failure_rate": len(differences) / compared if compared else 0.0,
    }


def is_data_table(book, spec: dict) -> bool:
    """Whether the range really is a Data Table rather than numbers that look like one.

    Excel exposes this as ``HasArray`` on a cell inside the table: a Data Table is stored as a
    multi-cell array formula, so a range of ordinary constants — which is exactly what the file
    contained before this stage ran — returns False.
    """
    sheet = book.Worksheets(spec["sheet"])
    cell = sheet.Range(f"B{spec['first_value_row']}")
    try:
        return bool(cell.HasArray)
    except Exception:  # pragma: no cover - defensive
        return False


def apply(path: pathlib.Path, ranges: dict[str, dict]) -> dict:
    """Attach every Data Table, save, and verify — the whole 5.2/5.3 sequence."""
    with com.workbook(path) as (_, book):
        # Idempotent: a range that is already a Data Table is left alone. Re-attaching over a
        # live array formula is how running the stage twice corrupts a workbook - criterion 5.9.
        pending = {name: spec for name, spec in ranges.items() if not is_data_table(book, spec)}
        attached = attach(book, pending)
        com.recalculate(book)
        report = verify(book, ranges)
        report["attached"] = attached
        report["already_attached"] = sorted(set(ranges) - set(pending))
        report["all_are_tables"] = all(is_data_table(book, spec) for spec in ranges.values())
        book.Save()
    return report
