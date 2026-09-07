"""The star is the consumer boundary — ADR 0020, phase 5 F-c and F-d."""

from __future__ import annotations

import pandas as pd
import pytest

from bellwether.data import generate
from bellwether.transform import semantic, star


@pytest.fixture(scope="session")
def tables() -> dict[str, pd.DataFrame]:
    return generate.generate()


@pytest.fixture(scope="session")
def built(tables) -> dict[str, pd.DataFrame]:
    return star.build_star(tables)


def test_the_split_redistributes_and_never_changes_a_total(tables, built) -> None:
    """The one property a materialised allocation must have."""
    source = float(tables["fact_gl"]["amount"].sum())
    starred = float(built["fact_gl"]["amount"].sum())
    assert abs(source - starred) < 0.01


def test_the_split_preserves_the_total_of_each_shared_account(tables, built) -> None:
    """Per account, not just in aggregate — an aggregate hides two errors that cancel."""
    shared = {"5000", "5010", "5020", "5220", "5300", "5310", "5320"}
    source = tables["fact_gl"]
    for code in sorted(shared):
        before = float(source.loc[source["account_code"] == code, "amount"].sum())
        after = float(
            built["fact_gl"].loc[built["fact_gl"]["account_code"] == code, "amount"].sum()
        )
        assert abs(before - after) < 0.01, code


def test_the_trial_balance_still_nets_to_zero_after_splitting(built) -> None:
    """Splitting a row into two must not break double entry — §9 check 11."""
    frame = built["fact_gl"].copy()
    frame["period"] = pd.to_datetime(frame["date"]).dt.to_period("M").astype(str)
    worst = frame.groupby(["version_name", "scenario_name", "period"])["amount"].sum().abs().max()
    assert worst < 0.01


def test_shared_cost_no_longer_sits_on_corporate_in_actual_periods(built) -> None:
    """B-2 — the failure this ADR exists to fix."""
    frame = built["fact_gl"]
    actual = frame[frame["version_name"] == "Actual"]
    shared = actual[actual["account_code"] == "5000"]
    assert not shared.empty
    assert set(shared["channel_allocation"].unique()) == {"DTC", "Wholesale"}
    assert (shared["split_basis"] == "units shipped").all()


def test_channel_contribution_is_a_group_by_not_a_calculation(tables, built) -> None:
    """5.14 — a consumer reads the star and groups. It re-implements nothing.

    This is the whole point of materialising the split: the numbers below come out of a
    ``groupby`` with no allocation logic anywhere in this test, which is exactly what a DAX
    measure will be doing.
    """
    frame = built["fact_gl"]
    actual = frame[
        (frame["version_name"] == "Actual") & (pd.to_datetime(frame["date"]).dt.year == 2025)
    ]
    contribution = {
        channel: semantic.evaluate_ladder(group, tables["dim_gl_account"])["EBITDA"]
        for channel, group in actual.groupby("channel_allocation")
    }
    assert contribution["DTC"] > 0
    assert contribution["Wholesale"] > 0
    assert contribution["Unallocated corporate"] < 0
    total = semantic.evaluate_ladder(actual, tables["dim_gl_account"])["EBITDA"]
    assert abs(sum(contribution.values()) - total) < 1.0


def test_shared_cost_is_split_only_where_units_were_measured(built) -> None:
    """Units are measured, and the split follows the measurement rather than the version.

    This used to assert that *every* forecast row was unallocated, which was true only because
    no forecast period overlapped a period with transaction facts. The FY2025 budget changed
    that: its months sit inside the actual years, so the units shipped in those months are
    measured and the split is real.

    Holding the mix at the measured activity of the month is also what a budget-versus-actual
    comparison at channel grain wants — it isolates the cost variance from the mix variance.
    """
    frame = built["fact_gl"]
    frame = frame.assign(year=pd.to_datetime(frame["date"]).dt.year)
    forecast = frame[frame["version_name"] != "Actual"]
    shared = forecast[forecast["account_code"] == "5000"]
    assert not shared.empty

    measured = shared[shared["year"].isin([2023, 2024, 2025])]
    unmeasured = shared[~shared["year"].isin([2023, 2024, 2025])]

    assert not measured.empty, "the FY2025 budget should have measured units behind it"
    assert (measured["split_basis"] == "units shipped").all()
    assert (unmeasured["split_basis"] == "none").all()
    assert (unmeasured["channel_allocation"] == "Unallocated corporate").all()


def test_every_gl_row_declares_how_it_was_attributed(built) -> None:
    basis = set(built["fact_gl"]["split_basis"].unique())
    assert basis <= {"direct", "units shipped", "none"}
    assert basis == {"direct", "units shipped", "none"}


def test_the_split_basis_is_monthly_not_annual(tables) -> None:
    """ADR 0020 — the DTC share swings far too much across the year for an annual ratio."""
    units = star.units_by_channel_month(tables)
    year = units[pd.to_datetime(units["month"]).dt.year == 2025]
    shares = year.pivot_table(index="month", columns="channel_name", values="units")
    dtc_share = shares["DTC"] / shares.sum(axis=1)
    assert dtc_share.max() - dtc_share.min() > 0.30, "an annual ratio would be defensible"


def test_the_star_carries_the_mapping_and_the_definitions(built) -> None:
    """A consumer needs both, and neither should be something it reconstructs."""
    assert "bridge_channel_allocation" in built
    assert "dim_metric" in built
    definitions = built["dim_metric"]
    assert set(definitions["name"]) == set(semantic.ALL_METRICS)
    assert "derivation" in definitions.columns
    assert "is_cost" in definitions.columns
