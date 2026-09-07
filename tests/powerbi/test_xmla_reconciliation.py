"""Criterion 5.15 — the measures, evaluated by Power BI's own engine.

The phase 5 spec called for exporting a table visual to CSV and comparing. This is better and it
is the same criterion: while a PBIP is open, Desktop hosts a local Analysis Services instance, and
a DAX query against it is evaluated by **the engine that will evaluate it in production** — real
filter context, real relationship propagation, real blank semantics.

Exporting a visual reads a *rendering*. The visual's own filters, its formatting and whatever
else the author put on the page sit between the measure and the number. A DAX query has none of
that in the way, so this closes the gap `test_dax_semantics.py` could only narrow: that module
evaluates the emitted DAX text in Python and says plainly it is not Power BI's engine. This is.

**Requires Desktop open with the project loaded.** The instance is ephemeral and its port changes
each session, so these skip when nothing is listening. A closed Desktop is not a defect.
"""

from __future__ import annotations

import pandas as pd
import pytest

from bellwether.data import generate
from bellwether.powerbi import xmla
from bellwether.transform import statements

pytestmark = pytest.mark.requires_powerbi

TOLERANCE = 0.01

#: What the DAX query calls each measure, and the semantic layer's name for the same thing.
MEASURES = {
    "NetRevenue": "Net Revenue",
    "EBITDA": "EBITDA",
    "GrossProfit": "Gross Profit",
}


@pytest.fixture(scope="module")
def engine_rows() -> pd.DataFrame:
    if not xmla.available():
        pytest.skip(
            "no live Power BI instance; open powerbi/northlake.pbip in Desktop and leave it open"
        )
    result = xmla.query(xmla.RECONCILIATION_DAX)
    assert result.get("ok"), result.get("error")
    frame = pd.DataFrame(result["rows"])
    assert not frame.empty, "the engine returned no rows"
    frame.columns = [c.strip("[]").split("[")[-1] for c in frame.columns]
    return frame


def test_the_engine_answers_at_all(engine_rows) -> None:
    """The connection itself. Without this the rest would skip silently and prove nothing."""
    assert len(engine_rows) > 0
    assert {"Month", "Version", "Scenario"} <= set(engine_rows.columns), engine_rows.columns


def test_every_measure_matches_the_oracle(engine_rows) -> None:
    """5.15 — row for row, at month x version x scenario, to the cent.

    Compared at grain rather than in total, because a total can agree while every month inside it
    is wrong in offsetting directions.
    """
    tables = generate.generate()
    expected = statements.metric_series(tables["fact_gl"], tables["dim_gl_account"])
    expected["Month"] = pd.to_datetime(expected["month"])

    actual = engine_rows.copy()
    actual["Month"] = pd.to_datetime(actual["Month"])
    merged = actual.merge(
        expected,
        left_on=["Month", "Version", "Scenario"],
        right_on=["Month", "version_name", "scenario_name"],
        how="inner",
    )
    assert len(merged) == len(actual), (
        f"{len(actual) - len(merged)} engine rows have no counterpart in the semantic layer"
    )

    worst = {}
    for dax_name, metric in MEASURES.items():
        column = next(c for c in merged.columns if c.startswith(dax_name))
        worst[metric] = float((merged[column].astype(float) - merged[metric]).abs().max())
    failures = {k: v for k, v in worst.items() if v > TOLERANCE}
    assert not failures, failures


def test_the_engine_covers_every_period_and_combination(engine_rows) -> None:
    """A reconciliation over half the grid would pass while saying nothing about the other half."""
    tables = generate.generate()
    expected = statements.metric_series(tables["fact_gl"], tables["dim_gl_account"])
    combinations = expected.groupby(["version_name", "scenario_name"]).ngroups
    actual = engine_rows.groupby(["Version", "Scenario"]).ngroups
    assert actual == combinations, f"engine {actual} combinations, semantic layer {combinations}"
    assert engine_rows["Month"].nunique() == expected["month"].nunique()
