"""Reading the built workbook back, without Excel.

Two things need this. The Excel reconciliation needs each formula cell's **cached** result — the
oracle's number, as xlsxwriter wrote it — so that recalculating can be compared against something
Excel did not produce. And the cross-artifact check (criterion 6.22) needs the workbook's figures
so they can be put next to Power BI's, with no Python arithmetic in between.

Both are file reads rather than COM reads, and deliberately so. `reconcile.py` explains at length
why asking Excel for the cached value is a comparison of a value against itself; the same logic
applies here. The workbook on disk is the artifact a reader receives, so that is what gets read.

Pure `zipfile` and `re`, so it runs on Linux in CI.
"""

from __future__ import annotations

import datetime as dt
import html
import pathlib
import re
import zipfile

_SHEET = re.compile(r'<sheet[^>]*name="([^"]+)"[^>]*r:id="([^"]+)"')
_RELATION = re.compile(r'<Relationship[^>]*Id="([^"]+)"[^>]*Target="([^"]+)"')
_CELL = re.compile(r'<c r="([A-Z]+\d+)"([^>]*)>(?:<f[^>]*>[^<]*</f>)?<v>([^<]*)</v>')
_SHARED = re.compile(r"<si>(.*?)</si>", re.DOTALL)
_TEXT = re.compile(r"<t[^>]*>([^<]*)</t>")
_REF = re.compile(r"([A-Z]+)(\d+)")

#: Excel's day zero, with the 1900 leap-year bug already accounted for by starting at 1899-12-30.
EPOCH = dt.datetime(1899, 12, 30)


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    member = "xl/sharedStrings.xml"
    if member not in archive.namelist():
        return []
    raw = archive.read(member).decode("utf-8")
    return [html.unescape("".join(_TEXT.findall(block))) for block in _SHARED.findall(raw)]


def _sheet_members(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
    rels_xml = archive.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    targets = dict(_RELATION.findall(rels_xml))
    members = {}
    for raw_name, relation in _SHEET.findall(workbook_xml):
        # Sheet names are XML-escaped here and plain over COM: "P&amp;L" is the sheet Excel calls
        # "P&L". Comparing the escaped form silently drops the sheet.
        target = targets.get(relation, "")
        member = f"xl/{target.lstrip('/')}" if not target.startswith("xl/") else target
        if member in archive.namelist():
            members[html.unescape(raw_name)] = member
    return members


def column_index(reference: str) -> tuple[int, int]:
    """``B7`` to a zero-based (row, column)."""
    letters, digits = _REF.match(reference).groups()
    column = 0
    for letter in letters:
        column = column * 26 + (ord(letter) - 64)
    return int(digits) - 1, column - 1


def sheet_cells(path: pathlib.Path, sheet: str) -> dict[tuple[int, int], object]:
    """Every populated cell of one sheet, by (row, column), as a float or a string.

    Shared strings are resolved, so a row label comes back as the label. Dates stay as their
    serial number — `to_month` turns one into a date when the caller knows the column is a date.
    """
    archive = zipfile.ZipFile(path)
    member = _sheet_members(archive).get(sheet)
    if member is None:
        raise KeyError(f"{path} has no sheet named {sheet!r}")
    strings = _shared_strings(archive)

    out: dict[tuple[int, int], object] = {}
    for reference, attributes, value in _CELL.findall(archive.read(member).decode("utf-8")):
        if 't="s"' in attributes:
            out[column_index(reference)] = strings[int(value)]
            continue
        try:
            out[column_index(reference)] = float(value)
        except ValueError:
            continue
    return out


def to_month(serial: float) -> dt.date:
    """An Excel date serial as a date. Month columns are written with `write_datetime`."""
    return (EPOCH + dt.timedelta(days=float(serial))).date()


def formula_values(path: pathlib.Path) -> dict[tuple[str, str], float]:
    """Every formula cell's cached result, by (sheet name, cell reference).

    These are the oracle's numbers, read out of the file xlsxwriter wrote. Nothing Excel says is
    involved in producing them, which is what makes `reconcile` a comparison.
    """
    archive = zipfile.ZipFile(path)
    out: dict[tuple[str, str], float] = {}
    for name, member in _sheet_members(archive).items():
        raw = archive.read(member).decode("utf-8")
        for reference, _, value in re.findall(
            r'<c r="([A-Z]+\d+)"([^>]*)><f[^>]*>[^<]*</f><v>([^<]*)</v>', raw
        ):
            try:
                out[(name, reference)] = float(value)
            except ValueError:
                # A formula returning text — the selection echo the statements carry. Not a
                # figure, so not part of a numeric reconciliation.
                continue
    return out


def data_grid(path: pathlib.Path, sheet: str = "Data") -> dict[tuple[str, dt.date], float]:
    """The workbook's lookup grid, keyed by its own row label and month.

    The grid is the workbook's complete set of figures — every version, scenario and line on the
    month axis — and the statements are lookups into it. Both the labels and the month headers are
    read from the file, so a row moving is a changed key rather than a silently shifted value.
    """
    cells = sheet_cells(path, sheet)
    months = {
        column: to_month(value)
        for (row, column), value in cells.items()
        if row == 0 and column > 0 and isinstance(value, float)
    }
    labels = {
        row: value
        for (row, column), value in cells.items()
        if column == 0 and row > 0 and isinstance(value, str)
    }
    return {
        (labels[row], months[column]): value
        for (row, column), value in cells.items()
        if row in labels and column in months and isinstance(value, float)
    }
