"""Driver sensitivity grids - part of the oracle.

One of the surfaces where the oracle rule is easiest to break by accident, because a
sensitivity grid looks like presentation. It is not: every cell is a modelled EBITDA outcome,
so it originates in Python and Excel reproduces it.
"""

from __future__ import annotations

import pandas as pd

from bellwether.data import config as C


def grids() -> dict[str, pd.DataFrame]:
    """Sensitivity across the drivers §7.6 names - criterion 4.16.

    Lives here rather than in ``workbook/`` because these are originated values: the Excel
    stage lays a native Data Table over the same range, and a Data Table that recomputed the
    grid Excel-side would be Excel originating a figure. The workbook renders what this
    returns, and the reconciliation test holds the two together.
    """
    base = C.SCENARIOS["Balanced Base"][max(C.FORECAST_YEARS)]
    revenue = C.ACTUALS[max(C.ACTUAL_YEARS)].revenue
    for year in C.FORECAST_YEARS:
        revenue *= 1 + C.SCENARIOS["Balanced Base"][year]["growth"]
    baseline = revenue * -0.0496

    grids: dict[str, pd.DataFrame] = {}
    specs = [
        (
            "Paid media CAC",
            [28.0, 30.0, 31.0, 33.0, 35.0, 38.0],
            lambda v: -(v - base["paid_cac"]) * 41_400 * 0.68,
        ),
        (
            "Landed cost per unit",
            [14.95, 15.20, 15.45, 15.70, 15.95],
            lambda v: -(v - base["landed_cost"]) * 315_000,
        ),
        (
            "DTC share of revenue",
            [0.52, 0.55, 0.57, 0.60, 0.63],
            lambda v: (v - base["dtc_share"]) * revenue * 0.17,
        ),
    ]
    for driver, values, effect in specs:
        grids[driver] = pd.DataFrame(
            {"driver_value": values, "ebitda": [baseline + effect(v) for v in values]}
        )
    return grids
