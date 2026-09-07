"""PDF and PNG export — criteria 6.26 to 6.29.

The last additive step. Excel renders what the headless build composed and writes two kinds of
artifact: the board pack as a PDF, and each exhibit as a PNG for the case study and the
distribution assets phase 7 needs.

**This module originates nothing and composes nothing.** It does not write a cell, choose a
figure or build a sentence. It exports named ranges whose contents and whose boundaries were both
decided in `transform/` and `workbook/` — which is why the export takes a range *name* rather
than coordinates. A coordinate here would be layout knowledge living in two places.

ADR 0022's fourth countermeasure has nothing automatable to offer for the PDF: reading our own
PDF back and finding our own figures in it proves the export ran, not that the pack is right, and
a page-count assertion is close to vacuous. The external authority is a person opening it, and
criterion 6.30 stays a manual gate, named as manual.
"""

from __future__ import annotations

import collections
import pathlib
import struct
import time
import zlib

from bellwether.excel_stage import com

#: ``xlTypePDF``.
FIXED_FORMAT_PDF = 0

#: ``xlScreen`` / ``xlBitmap`` — copy as it appears, then paste as a bitmap.
COPY_AS_SHOWN = 1
COPY_BITMAP = 2

#: The clipboard needs a moment between the copy and the paste.
CLIPBOARD_SETTLE = 0.4

#: An exported picture is blank if almost every pixel is the same colour. Excel writes a
#: correctly sized PNG whether or not the paste landed, so the file existing proves nothing —
#: this is the check that tells the two apart.
BLANK_THRESHOLD = 0.97

#: Excel copies at screen resolution and a pasted bitmap does not scale, so the picture is
#: exported at the size the range occupies. Zooming the window first was tried and made the
#: canvas and the picture disagree, which produced large, almost entirely blank images.


def export_pdf(book, path: pathlib.Path, sheet_name: str = "Board pack") -> pathlib.Path:
    """Criterion 6.26 — the board pack, as the client-facing artifact."""
    sheet = book.Worksheets(sheet_name)
    sheet.PageSetup.Orientation = 2  # xlLandscape
    sheet.PageSetup.Zoom = False
    sheet.PageSetup.FitToPagesWide = 1
    sheet.PageSetup.FitToPagesTall = False
    sheet.ExportAsFixedFormat(FIXED_FORMAT_PDF, str(pathlib.Path(path).resolve()))
    return pathlib.Path(path)


def page_count(book, sheet_name: str = "Board pack") -> int:
    """How many pages the pack will print to.

    Not a proof of anything — see the module docstring — but a zero-page or fifty-page pack is a
    layout failure worth catching before a human is asked to look.
    """
    sheet = book.Worksheets(sheet_name)
    return int(sheet.PageSetup.Pages.Count)


@com.retry()
def export_png(book, named_range: str, path: pathlib.Path) -> pathlib.Path:
    """Criterion 6.28 — one exhibit, at readable resolution.

    Taken by range **name**. The export does not know where the exhibit sits, which is the point:
    moving a table in the workbook must not require editing this file.
    """
    target = book.Names(named_range).RefersToRange
    sheet = target.Worksheet
    sheet.Activate()

    # The chart is created **before** the copy. Adding a ChartObject clears the clipboard, so
    # creating it after CopyPicture pastes nothing — and Excel then exports a correctly sized,
    # entirely blank PNG without raising. That failure cost several rounds precisely because the
    # output looked like a success.
    chart = sheet.ChartObjects().Add(0, 0, target.Width, target.Height)
    try:
        chart.Chart.ChartArea.Border.LineStyle = 0
        # Positional, for the same reason Range.Table is: pywin32's late binding routes a
        # keyword to the first parameter regardless of its name.
        target.CopyPicture(COPY_AS_SHOWN, COPY_BITMAP)
        time.sleep(CLIPBOARD_SETTLE)
        chart.Activate()
        chart.Chart.Paste()
        chart.Chart.Export(str(pathlib.Path(path).resolve()), "PNG")
    finally:
        chart.Delete()
    return pathlib.Path(path)


def export_all(path: pathlib.Path, named_ranges: list[str], out_dir: pathlib.Path) -> dict:
    """Export the pack and every exhibit. Returns what was written."""
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = pathlib.Path(path).parent / "northlake-board-pack.pdf"

    written: dict = {"pdf": None, "pages": 0, "png": []}
    # Visible, only here. CopyPicture renders what is on screen and fails against a hidden
    # instance; every other COM step in this project runs invisibly and should stay that way.
    with com.workbook(path, visible=True) as (_, book):
        com.recalculate(book)
        written["pdf"] = export_pdf(book, pdf)
        written["pages"] = page_count(book)
        for name in named_ranges:
            target = out_dir / f"{name}.png"
            export_png(book, name, target)
            written["png"].append(target)

    # Checked after the fact, not trusted. A blank export is the failure mode that looks most
    # like success: the file is there, its dimensions are right, and it contains nothing.
    written["blank"] = [p for p in written["png"] if is_blank(p)]
    return written


def uniformity(path: pathlib.Path) -> float:
    """The share of the image made of its single most common byte.

    A crude measure and the right one: a table of numbers is never 97% one value, and a blank
    canvas always is. Excel exports a PNG of the correct dimensions whether or not the paste
    landed, so size and existence say nothing.
    """
    data = pathlib.Path(path).read_bytes()
    compressed, index = b"", 8
    while index < len(data):
        length = struct.unpack(">I", data[index : index + 4])[0]
        kind = data[index + 4 : index + 8]
        if kind == b"IDAT":
            compressed += data[index + 8 : index + 8 + length]
        index += 12 + length
    raw = zlib.decompress(compressed)
    if not raw:
        return 1.0
    return collections.Counter(raw).most_common(1)[0][1] / len(raw)


def is_blank(path: pathlib.Path) -> bool:
    return uniformity(path) >= BLANK_THRESHOLD
