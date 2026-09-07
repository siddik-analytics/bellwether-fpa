"""The FY2025 budget — phase 6 G-a, and the resolution of R-1.

`semantic.decompose` has always taken an `actual` and a `budget` argument. Until now they could
never both be populated for the same period: Budget covered FY2026-28, Actual covered FY2023-25,
and the overlap was zero months. Performance variance — the first of the three decompositions
§3.3 requires — was uncomputable on the generated data.

The budget Northlake approved at the end of FY2024 fixes that, and it is **wrong in exactly two
ways**, both dateable and both already in §1.3:

1. Product cost holds at FY2024's $14.12; the supplier increase landed in April 2025.
2. The food-storage launch performs to plan; it ran ~35% below.

Everything else is budgeted at what happened. That is the point: a budget that differs everywhere
produces a residual that swamps both real effects, and commentary can only attribute a movement
it can decompose.
"""

from __future__ import annotations

import pandas as pd
import pytest

from bellwether.data import config as C
from bellwether.data import forecast, generate
from bellwether.transform import statements


@pytest.fixture(scope="module")
def data() -> dict[str, pd.DataFrame]:
    return generate.generate()


def test_budget_and_actual_now_share_a_year(data) -> None:
    """R-1 — the finding this exists to resolve."""
    series = statements.metric_series(data["fact_gl"], data["dim_gl_account"])
    series["year"] = pd.to_datetime(series["month"]).dt.year
    budget = set(series.loc[series["version_name"] == "Budget", "year"])
    actual = set(series.loc[series["version_name"] == "Actual", "year"])
    assert C.BUDGET_YEAR in budget & actual, (budget, actual)
    for version in ("Budget", "Actual"):
        months = series[(series["version_name"] == version) & (series["year"] == C.BUDGET_YEAR)]
        assert len(months) == 12, version


def test_exactly_two_drivers_differ_from_what_happened(data) -> None:
    """Wrong in specific ways rather than noisy. The whole design rests on this."""
    drivers = forecast.budget_drivers(100_000.0)
    actual = C.ACTUALS[C.BUDGET_YEAR]
    differing = {
        key
        for key, value in drivers.items()
        if key != "growth" and abs(value - getattr(actual, key)) > 1e-9
    }
    assert differing == {"landed_cost"}, differing
    assert drivers["landed_cost"] == C.ACTUALS[C.BUDGET_YEAR - 1].landed_cost


def test_the_launch_shortfall_is_derived_not_stated(data) -> None:
    """From the realised revenue of the launch SKUs, so it stays true if the generator changes."""
    products = data["dim_product"]
    launch = products[products["lifecycle_state"] == "launch"]
    assert not launch.empty
    assert set(launch["product_family"]) == {"Food storage"}
    assert launch["launch_date"].dt.year.unique().tolist() == [C.BUDGET_YEAR]

    plan = data["fact_forecast_monthly"]
    budgeted = plan[
        (plan["version_name"] == "Budget")
        & (pd.to_datetime(plan["month"]).dt.year == C.BUDGET_YEAR)
    ]["revenue"].sum()
    assert budgeted > C.ACTUALS[C.BUDGET_YEAR].revenue, "the budget assumed the launch performed"


def test_the_variance_has_the_two_causes_and_the_right_signs(data) -> None:
    """Revenue short because the launch missed; cost of sales over because product cost rose."""
    series = statements.metric_series(data["fact_gl"], data["dim_gl_account"])
    series["year"] = pd.to_datetime(series["month"]).dt.year
    year = series[series["year"] == C.BUDGET_YEAR]
    budget = year[year["version_name"] == "Budget"]
    actual = year[year["version_name"] == "Actual"]

    assert actual["Net Revenue"].sum() < budget["Net Revenue"].sum(), "the launch missed"
    assert actual["Cost of Sales"].sum() > budget["Cost of Sales"].sum(), "product cost rose"
    assert actual["EBITDA"].sum() < budget["EBITDA"].sum(), "both are unfavourable"


def test_the_budget_uses_the_same_arithmetic_as_the_forecast(data) -> None:
    """A budget computed differently from the plan it is compared against puts method into the
    variance. Both go through `_year_rows`."""
    plan = forecast.budget_pl(100_000.0)
    forecast_shape = set(forecast.monthly_pl("Balanced Base", 10_600_000.0).columns)
    assert set(plan.columns) == forecast_shape
    assert len(plan) == 12


def test_the_budget_opens_on_the_prior_year_close(data) -> None:
    """A budget approved at the end of FY2024 cannot open on a balance sheet that includes 2025."""
    ledger = data["fact_gl"]
    budget = ledger[ledger["version_name"] == "Budget"]
    openings = budget[budget["memo"] == "Opening balance sheet"]
    months = pd.to_datetime(openings["date"]).dt.to_period("M").unique()
    assert len(months) == 1, f"the budget opened {len(months)} times"
    assert str(months[0]) == f"{C.BUDGET_YEAR}-01"
