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
    # `fact_metric[Month]` -> `Month`, `[EBITDA]` -> `engine_EBITDA`. The measures are prefixed
    # because the semantic layer uses the same names, and an unprefixed merge silently suffixes
    # both sides — which reads as a missing column rather than as the collision it is.
    renamed = []
    for column in frame.columns:
        bare = column.rsplit("[", 1)[-1].rstrip("]")
        renamed.append(bare if "[" in column and not column.startswith("[") else f"engine_{bare}")
    frame.columns = renamed
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
        engine = merged[f"engine_{dax_name}"].astype(float)
        worst[metric] = float((engine - merged[metric].astype(float)).abs().max())
    failures = {k: v for k, v in worst.items() if v > TOLERANCE}
    assert not failures, failures
    print("\n5.15 - Power BI's engine against the oracle, 0.01 tolerance:")
    for metric, delta in sorted(worst.items()):
        print(f"  {metric:16s} rows {len(merged):>4}  worst delta {delta:.6f}")


def test_the_engine_covers_every_period_and_combination(engine_rows) -> None:
    """A reconciliation over half the grid would pass while saying nothing about the other half."""
    tables = generate.generate()
    expected = statements.metric_series(tables["fact_gl"], tables["dim_gl_account"])
    combinations = expected.groupby(["version_name", "scenario_name"]).ngroups
    actual = engine_rows.groupby(["Version", "Scenario"]).ngroups
    assert actual == combinations, f"engine {actual} combinations, semantic layer {combinations}"
    assert engine_rows["Month"].nunique() == expected["month"].nunique()


def test_the_reconciliation_can_actually_fail(engine_rows) -> None:
    """The negative control — ADR 0022's first countermeasure, applied here.

    Zero differences across 360 rows is only evidence if this comparison is capable of producing
    a difference. One engine value is shifted by a cent and the same arithmetic must catch it,
    at exactly one row.
    """
    tables = generate.generate()
    expected = statements.metric_series(tables["fact_gl"], tables["dim_gl_account"])
    expected["Month"] = pd.to_datetime(expected["month"])

    tampered = engine_rows.copy()
    tampered["Month"] = pd.to_datetime(tampered["Month"])
    tampered.loc[tampered.index[0], "engine_EBITDA"] = (
        float(tampered.loc[tampered.index[0], "engine_EBITDA"]) + 0.02
    )

    merged = tampered.merge(
        expected,
        left_on=["Month", "Version", "Scenario"],
        right_on=["Month", "version_name", "scenario_name"],
        how="inner",
    )
    delta = (merged["engine_EBITDA"].astype(float) - merged["EBITDA"].astype(float)).abs()
    assert (delta > TOLERANCE).sum() == 1, "the comparison did not notice a planted discrepancy"
