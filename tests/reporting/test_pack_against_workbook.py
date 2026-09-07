"""Criterion 6.22, first leg — the pack against the built workbook.

6.22 asks that every figure in the pack equals the workbook's and Power BI's figure for the same
thing. Until now that held *by construction*: all three read the same semantic layer, so of course
they agree. That is an argument, not a test, and it is precisely the shape ADR 0022 is about — a
check whose oracle is the thing under test cannot fail.

So the chain is closed one leg at a time, and each leg reads a **built artifact** rather than the
code that built it:

* here — the pack's exhibit figures against `build/northlake-model.xlsx`, read out of the file;
* `tests/powerbi/test_workbook_against_engine.py` — that workbook file against Power BI's engine.

Neither leg has Python arithmetic in the middle. This one is headless and runs in CI; the other
needs Desktop open and does not.
"""

from __future__ import annotations

import pytest

from bellwether.data import config as C
from bellwether.paths import BUILD_DIR
from bellwether.transform import pack
from bellwether.workbook import read

TOLERANCE = 0.01
WORKBOOK = BUILD_DIR / "northlake-model.xlsx"


@pytest.fixture(scope="module")
def grid() -> dict:
    if not WORKBOOK.exists():
        pytest.skip(f"{WORKBOOK} has not been built; run python -m bellwether.build")
    return read.data_grid(WORKBOOK)


@pytest.fixture(scope="module")
def sections(star_tables) -> list:
    return pack.compose(star_tables, star_tables["fact_gl"])


def workbook_total(grid: dict, version: str, scenario: str, line: str, year: int) -> float:
    """One line of the workbook, summed over a year, addressed by its own row label."""
    key = f"{version}|{scenario}|PL:{line}"
    values = [v for (label, month), v in grid.items() if label == key and month.year == year]
    assert values, f"the workbook has no row {key!r} in {year}"
    return float(sum(values))


def exhibit(sections: list, key: str) -> pack.Exhibit:
    return next(e for section in sections for e in section.exhibits if e.key == key)


def test_the_scenario_comparison_matches_the_workbook(grid, sections) -> None:
    """Four scenarios, two measures, against the file a reader opens."""
    table = exhibit(sections, "scenario_comparison").table
    horizon = max(C.FORECAST_YEARS)
    checked = 0
    for _, row in table.iterrows():
        for column, line in (
            (f"FY{horizon} net revenue", "Net Revenue"),
            (f"FY{horizon} EBITDA", "EBITDA"),
        ):
            expected = workbook_total(grid, "Latest Forecast", row["Scenario"], line, horizon)
            assert abs(float(row[column]) - expected) < TOLERANCE, (
                f"{row['Scenario']} {line}: pack {row[column]:,.2f}, workbook {expected:,.2f}"
            )
            checked += 1
    assert checked == 8


def test_the_channel_contribution_total_matches_the_workbook(grid, sections) -> None:
    """The exhibit's own total row. The channel rows have no counterpart — the workbook carries
    no channel grain — and claiming to check them would be worse than checking fewer figures."""
    table = exhibit(sections, "channel_contribution").table
    year = max(C.ACTUAL_YEARS)
    total = table[table[""] == f"FY{year} total"].iloc[0]
    for column, line in (("Net revenue", "Net Revenue"), ("Contribution", "EBITDA")):
        expected = workbook_total(grid, "Actual", "Balanced Base", line, year)
        assert abs(float(total[column]) - expected) < TOLERANCE, (
            f"{line}: pack {total[column]:,.2f}, workbook {expected:,.2f}"
        )


def test_the_bridge_endpoints_match_the_workbook(grid, sections) -> None:
    """Both sides of the variance, against the workbook's budget and actual rows.

    The effects have no workbook counterpart, but the two totals they bridge between do — and if
    those agree, the exhibit is bridging the same movement the workbook shows.
    """
    year = max(C.ACTUAL_YEARS)
    decision = next(s for s in sections if s.title == "What follows")
    against_budget = next(b for b in decision.blocks if b.title == "Performance against budget")
    headline = against_budget.sentences[0]
    actual = workbook_total(grid, "Actual", "Balanced Base", "Gross Profit", year)
    budget = workbook_total(grid, "Budget", "Balanced Base", "Gross Profit", year)
    reported_total, movement = headline.numbers
    assert abs(reported_total - actual) < TOLERANCE, (headline.text, actual)
    assert abs(movement - (actual - budget)) < TOLERANCE, (headline.text, actual - budget)


def test_the_comparison_can_actually_fail(grid, sections) -> None:
    """ADR 0022's negative control. Zero differences mean nothing from a check that cannot find
    one, so a cent is moved in the workbook's grid and the same arithmetic must catch it."""
    table = exhibit(sections, "scenario_comparison").table
    horizon = max(C.FORECAST_YEARS)
    scenario = table.iloc[0]["Scenario"]
    key = f"Latest Forecast|{scenario}|PL:Net Revenue"
    tampered = dict(grid)
    month = next(m for (label, m) in tampered if label == key and m.year == horizon)
    tampered[(key, month)] += 0.02

    expected = workbook_total(tampered, "Latest Forecast", scenario, "Net Revenue", horizon)
    delta = abs(float(table.iloc[0][f"FY{horizon} net revenue"]) - expected)
    assert delta > TOLERANCE, "the comparison did not notice a planted discrepancy"


def test_every_workbook_row_is_a_version_scenario_and_line(grid) -> None:
    """The addressing itself. A key the test cannot parse is a row it would silently skip, which
    is how a cross-artifact check quietly shrinks to nothing."""
    labels = {label for label, _ in grid}
    assert len(labels) > 100, len(labels)
    for label in labels:
        version, scenario, line = label.split("|")
        assert version and scenario and line, label
    months = {month for _, month in grid}
    assert len(months) == 12 * len(C.ACTUAL_YEARS + C.FORECAST_YEARS), sorted(months)[:3]


def test_the_pack_and_the_workbook_are_built_from_the_same_data(grid, sections) -> None:
    """A stale workbook is the failure this leg exists to catch, and it would show up as a
    difference in every figure rather than one. Named so the message says so."""
    year = max(C.ACTUAL_YEARS)
    lead = next(s for s in sections if s.title == "Position")
    revenue = workbook_total(grid, "Actual", "Balanced Base", "Net Revenue", year)
    assert f"{revenue / 1_000_000:,.2f}M" in lead.lead, (
        f"the pack's lead does not quote the workbook's FY{year} revenue of {revenue:,.2f} — "
        "one of the two is stale"
    )
