"""Driver sensitivity grids — part of the oracle.

One of the surfaces where the oracle rule is easiest to break by accident, because a sensitivity
grid looks like presentation. It is not: every cell is a modelled EBITDA outcome, so it
originates in Python and Excel reproduces it.

Each driver is exposed as a **baseline plus a slope** rather than only as a table of results.
That is what lets the Excel stage lay a native Data Table over the grid: the workbook carries an
input cell and one formula, Excel varies the input and recomputes the column, and criterion 5.3
asserts the recomputed column still equals what this module produced. Without the slope the
sheet could only hold constants, and a Data Table over constants is decoration.

The response is linear in each driver by construction. That is a modelling choice and a
limitation worth naming: it is a first-order sensitivity around the operating plan, not a
re-solve of the model at each point, and it is honest over the range the grids cover rather than
across the whole domain.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from bellwether.data import config as C

#: FY2028 EBITDA margin under the operating plan, from the scenario probe. The grids move around
#: this point rather than re-solving the model at each one.
BASELINE_MARGIN = -0.0496


@dataclass(frozen=True)
class Driver:
    """One sensitivity: where the plan sits, how far EBITDA moves per unit, and what to show."""

    name: str
    #: The operating plan's value for this driver — the point the grid pivots around.
    base_value: float
    #: Change in FY2028 EBITDA per one unit of change in the driver.
    slope: float
    #: The values the grid is evaluated at.
    values: tuple[float, ...]
    format_string: str = "$#,##0.00"

    def ebitda(self, value: float, baseline: float) -> float:
        return baseline + self.slope * (value - self.base_value)


def _baseline_revenue() -> float:
    revenue = C.ACTUALS[max(C.ACTUAL_YEARS)].revenue
    for year in C.FORECAST_YEARS:
        revenue *= 1 + C.SCENARIOS["Balanced Base"][year]["growth"]
    return revenue


def baseline_ebitda() -> float:
    """FY2028 EBITDA under the operating plan — the point every grid pivots around."""
    return _baseline_revenue() * BASELINE_MARGIN


def drivers() -> dict[str, Driver]:
    """The drivers §7.6 names as sensitivities — criterion 4.16."""
    plan = C.SCENARIOS["Balanced Base"][max(C.FORECAST_YEARS)]
    revenue = _baseline_revenue()
    return {
        "Paid media CAC": Driver(
            name="Paid media CAC",
            base_value=float(plan["paid_cac"]),
            # A dollar on CAC costs a dollar on every paid-acquired customer.
            slope=-41_400 * 0.68,
            values=(28.0, 30.0, 31.0, 33.0, 35.0, 38.0),
        ),
        "Landed cost per unit": Driver(
            name="Landed cost per unit",
            base_value=float(plan["landed_cost"]),
            slope=-315_000.0,
            values=(14.95, 15.20, 15.45, 15.70, 15.95),
        ),
        "DTC share of revenue": Driver(
            name="DTC share of revenue",
            base_value=float(plan["dtc_share"]),
            # The margin difference between the two channels, applied to revenue that moves.
            slope=revenue * 0.17,
            values=(0.52, 0.55, 0.57, 0.60, 0.63),
            format_string="0.0%",
        ),
    }


def grids() -> dict[str, pd.DataFrame]:
    """Every driver's grid as a frame of driver value against modelled FY2028 EBITDA."""
    baseline = baseline_ebitda()
    return {
        name: pd.DataFrame(
            {
                "driver_value": list(driver.values),
                "ebitda": [driver.ebitda(value, baseline) for value in driver.values],
            }
        )
        for name, driver in drivers().items()
    }
