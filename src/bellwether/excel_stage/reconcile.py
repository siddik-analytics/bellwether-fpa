"""Cross-implementation reconciliation — criteria 5.1 and 5.3, carried from phase 4.

This is the test the architecture is built around. The headless build writes every formula cell
with **both** its formula and the oracle's value as the cached result; this stage asks Excel to
recompute from the formulas and compares the result against that cached value.

Two independent implementations of one specification. Either one drifting shows up here and
nowhere else, which is why `.claude/rules/excel-com.md` calls it a first-class deliverable
rather than a smoke test.

**The cached value is read from the file, not from Excel.** That distinction is the whole test.
An earlier version of this module read each cell through COM before recalculating and again
after, which looked equivalent and was not: Excel evaluates formulas as it opens a workbook, so
the "before" read already held Excel's own answer and the comparison was a value against itself.
It reported zero differences on a workbook with a deliberately wrong cached value. The oracle's
number lives in the `<v>` element xlsxwriter wrote, so that is where it has to be read from.

The comparison covers **every** formula cell, not a sample and not the totals. The failure this
catches — a formula that is subtly wrong but whose cached value is right — is invisible in any
aggregate, because the aggregate is built from the cached values that are correct.
"""

from __future__ import annotations

import html
import pathlib
import re
import zipfile

from bellwether.excel_stage import com

#: Contract §9 and `CLAUDE.md`: workbook values match the oracle within a cent.
TOLERANCE = 0.01

_SHEET = re.compile(r'<sheet[^>]*name="([^"]+)"[^>]*r:id="([^"]+)"')
_RELATION = re.compile(r'<Relationship[^>]*Id="([^"]+)"[^>]*Target="([^"]+)"')
_CELL = re.compile(r'<c r="([A-Z]+\d+)"[^>]*>(?:<f[^>]*>(?:[^<]*)</f>)<v>([^<]*)</v>')


def cached_values(path: pathlib.Path) -> dict[tuple[str, str], float]:
    """Every formula cell's cached result, read straight out of the workbook file.

    These are the oracle's numbers. Nothing Excel says is involved in producing them, which is
    what makes the comparison a comparison.
    """
    archive = zipfile.ZipFile(path)
    workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
    rels_xml = archive.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    targets = dict(_RELATION.findall(rels_xml))

    out: dict[tuple[str, str], float] = {}
    for raw_name, relation in _SHEET.findall(workbook_xml):
        # Sheet names are XML-escaped in workbook.xml and plain over COM: "P&amp;L" is the
        # sheet Excel calls "P&L". Comparing the escaped form silently drops the sheet.
        name = html.unescape(raw_name)
        target = targets.get(relation, "")
        member = f"xl/{target.lstrip('/')}" if not target.startswith("xl/") else target
        if member not in archive.namelist():
            continue
        for cell, value in _CELL.findall(archive.read(member).decode("utf-8")):
            try:
                out[(name, cell)] = float(value)
            except ValueError:
                # A formula returning text — the selection echo the statements carry. Not a
                # figure, so not part of a numeric reconciliation.
                continue
    return out


def reconcile(path: pathlib.Path, tolerance: float = TOLERANCE) -> dict:
    """Recalculate the workbook and compare every formula against its cached oracle value.

    Returns a report rather than raising, so a caller can present the failure rate instead of a
    single assertion message. A reconciliation that fails is information about where the two
    implementations disagree, and a bare ``assert`` throws that away.
    """
    cached = cached_values(path)

    with com.workbook(path) as (_, book):
        com.recalculate(book)
        recalculated = {
            (sheet, cell): (formula, value)
            for sheet, cell, formula, value in com.formula_cells(book)
        }

    differences: list[com.Difference] = []
    compared = 0
    missing: list[tuple[str, str]] = []
    for key, oracle_value in cached.items():
        if key not in recalculated:
            missing.append(key)
            continue
        formula, excel_value = recalculated[key]
        compared += 1
        if abs(oracle_value - excel_value) > tolerance:
            differences.append(
                com.Difference(
                    sheet=key[0],
                    cell=key[1],
                    formula=formula,
                    cached=oracle_value,
                    recalculated=excel_value,
                )
            )

    differences.sort(key=lambda d: d.delta, reverse=True)
    return {
        "compared": compared,
        "cached_cells": len(cached),
        "missing": missing,
        "differences": differences,
        "failure_rate": len(differences) / compared if compared else 0.0,
        "worst": differences[0].delta if differences else 0.0,
        "by_sheet": _by_sheet(differences),
    }


def _by_sheet(differences: list[com.Difference]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for difference in differences:
        counts[difference.sheet] = counts.get(difference.sheet, 0) + 1
    return counts


def format_report(report: dict, limit: int = 10) -> str:
    """A readable summary. Used by the CLI and by the test's assertion message."""
    lines = [
        f"compared {report['compared']:,} of {report['cached_cells']:,} cached formula cells",
        f"differences {len(report['differences']):,} "
        f"({report['failure_rate']:.2%}), worst {report['worst']:,.4f}",
    ]
    if report["missing"]:
        lines.append(f"not found in Excel: {len(report['missing']):,} — {report['missing'][:3]}")
    if report["by_sheet"]:
        lines.append("by sheet: " + ", ".join(f"{k} {v}" for k, v in report["by_sheet"].items()))
    for difference in report["differences"][:limit]:
        lines.append(f"  {difference}")
    remaining = len(report["differences"]) - limit
    if remaining > 0:
        lines.append(f"  ... and {remaining:,} more")
    return "\n".join(lines)
