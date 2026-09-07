"""What a figure is, and how it reads — one convention per context.

The board pack's first review found percent formats on dollar columns: a revolver drawn to $0
printed as `0.0%`, and the bridge's unexplained residual — the row whose entire purpose is to
carry an unattributed *amount* — printed as `(0.0%)`. The cause was a renderer guessing:

    style = "percent" if abs(value) <= 1.5 else "money"

A value cannot say what it measures. `0.0` is a dollar amount, a rate, a count and a flag with
equal plausibility, and a guess that is right for most cells is a guess that is silently wrong for
the ones that matter — zero balances and empty residuals, which are exactly the figures a reader
most needs to read correctly.

So a unit is **declared where the figure is composed**, next to the code that knows what it means,
and every consumer renders from that declaration. `Exhibit.units` carries one per column and
`tests/reporting/test_pack.py` asserts no numeric column goes undeclared. It is the same boundary
as everywhere else in this project: `transform/` decides what a number is, and the workbook,
Power BI and the PDF render what they are told.

Two conventions, one per context:

* **Prose** — `money()`. Millions to two decimals above $1M, whole dollars below, always with a
  currency symbol and never with a bare minus sign. `$10.60M`, `$163,656`.
* **Tables** — Excel number formats resolved from the declared unit, so alignment, negatives and
  decimals are consistent down a column rather than per cell.

Mixing them is what produced "$10.60M ... 10,738,185" inside one paragraph, so the bridge's driver
strings now go through `money()` like everything else a reader sees.
"""

from __future__ import annotations

import math

#: The declared units. A column is one of these; there is no default and no inference.
MONEY = "money"
PERCENT = "percent"
COUNT = "count"
FLAG = "flag"
TEXT = "text"

UNITS = (MONEY, PERCENT, COUNT, FLAG, TEXT)

#: Units that must be written as numbers rather than as text.
NUMERIC = (MONEY, PERCENT, COUNT)


def money(amount: float) -> str:
    """A figure a reader can say out loud. Signed by direction, never by a minus sign alone."""
    magnitude = abs(amount)
    if magnitude >= 1_000_000:
        return f"${magnitude / 1_000_000:,.2f}M"
    return f"${magnitude:,.0f}"


def ratio(numerator: float, denominator: float) -> float:
    """A rate, or `nan` when there is no denominator to divide by.

    Returning `0.0` for an undefined ratio is what put "contribution margin 0.0%" against a
    corporate cost block that has no revenue at all. Nought percent and no percent are different
    statements and a reader cannot tell them apart once both are printed as `0.0%`.
    """
    if not denominator:
        return math.nan
    return numerator / denominator


def is_undefined(value) -> bool:
    return isinstance(value, float) and math.isnan(value)
