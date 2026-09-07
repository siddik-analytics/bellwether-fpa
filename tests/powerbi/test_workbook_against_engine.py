"""Criterion 6.22, second leg — the built workbook against Power BI's engine.

The README's strongest claim is that one set of definitions drives Excel, Power BI and the board
pack. Until now that was argued rather than tested: all three read the same semantic layer, so of
course they agreed, and no check could have failed. ADR 0022 is about exactly that shape.

This leg has no Python arithmetic in it. The figures on one side are read out of
`build/northlake-model.xlsx` — the file a reader opens — and the figures on the other are computed
by the Analysis Services instance Desktop hosts while the PBIP is loaded. Two artifacts, two
readers, one comparison, at month x version x scenario.

What it can catch that `test_xmla_reconciliation.py` cannot: that leg checks the engine against
the semantic layer *as it is now*. If the workbook were built from different data — a stale file,
a rebuild that only half ran — it would still pass while the two deliverables disagreed. Comparing
the artifacts to each other is what notices.

**Requires both artifacts to exist.** The workbook must be built and Desktop must be open with
`powerbi/northlake.pbip` loaded. Neither is a defect when absent, so this skips.
"""

from __future__ import annotations

import pandas as pd
import pytest

from bellwether.paths import BUILD_DIR
from bellwether.powerbi import xmla
from bellwether.workbook import read

pytestmark = pytest.mark.requires_powerbi

TOLERANCE = 0.01
WORKBOOK = BUILD_DIR / "northlake-model.xlsx"

#: What the DAX query calls each measure, and the label the workbook's own grid gives the same
#: line. Both names are read from the artifacts; neither is a Python variable.
MEASURES = {
    "NetRevenue": "PL:Net Revenue",
    "EBITDA": "PL:EBITDA",
    "GrossProfit": "PL:Gross Profit",
}


@pytest.fixture(scope="module")
def workbook_grid() -> dict:
    if not WORKBOOK.exists():
        pytest.skip(f"{WORKBOOK} has not been built; run python -m bellwether.build")
    return read.data_grid(WORKBOOK)


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
    frame.columns = [column.rsplit("[", 1)[-1].rstrip("]") for column in frame.columns]
    frame["Month"] = pd.to_datetime(frame["Month"]).dt.date
    return frame


def test_the_two_artifacts_agree_row_for_row(workbook_grid, engine_rows) -> None:
    """6.22 — every figure, at the grain both artifacts carry.

    Compared row by row rather than in total: two totals can agree while every month inside them
    is wrong in offsetting directions, which is the failure a summary check is blind to.
    """
    compared, worst, missing = 0, {}, []
    for _, row in engine_rows.iterrows():
        for measure, line in MEASURES.items():
            key = (f"{row['Version']}|{row['Scenario']}|{line}", row["Month"])
            if key not in workbook_grid:
                missing.append(key)
                continue
            delta = abs(float(row[measure]) - workbook_grid[key])
            compared += 1
            worst[measure] = max(worst.get(measure, 0.0), delta)

    assert not missing, f"{len(missing)} engine figures have no workbook row — {missing[:3]}"
    failures = {k: v for k, v in worst.items() if v > TOLERANCE}
    assert not failures, failures
    assert compared == len(engine_rows) * len(MEASURES)
    print(f"\n6.22 - the workbook file against Power BI's engine, {compared:,} figures:")
    for measure, delta in sorted(worst.items()):
        print(f"  {measure:12s} worst delta {delta:.6f}")


def test_the_engine_covers_the_whole_workbook_grid(workbook_grid, engine_rows) -> None:
    """A comparison over half the grid would pass while saying nothing about the other half."""
    from_workbook = {
        tuple(label.split("|")[:2])
        for label, _ in workbook_grid
        if label.split("|")[2] in MEASURES.values()
    }
    from_engine = set(zip(engine_rows["Version"], engine_rows["Scenario"], strict=True))
    assert from_workbook == from_engine, {
        "workbook only": from_workbook - from_engine,
        "engine only": from_engine - from_workbook,
    }


def test_the_comparison_can_actually_fail(workbook_grid, engine_rows) -> None:
    """ADR 0022's first countermeasure. Zero differences across thousands of figures is evidence
    only if this arithmetic can produce one, so a cent is moved and it must be found, once."""
    tampered = dict(workbook_grid)
    row = engine_rows.iloc[0]
    key = (f"{row['Version']}|{row['Scenario']}|{MEASURES['EBITDA']}", row["Month"])
    assert key in tampered, key
    tampered[key] += 0.02

    caught = sum(
        1
        for _, engine_row in engine_rows.iterrows()
        for measure, line in MEASURES.items()
        if abs(
            float(engine_row[measure])
            - tampered[
                (f"{engine_row['Version']}|{engine_row['Scenario']}|{line}", engine_row["Month"])
            ]
        )
        > TOLERANCE
    )
    assert caught == 1, f"planted one discrepancy, the comparison found {caught}"
