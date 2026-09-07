"""D-1 — the forecast ledger posts its financing. Criteria 6.1 to 6.6.

`post_financing` existed, was exported, and was never called. The schedule carried $370,351 of
interest and $245,310 of fees and the ledger carried none of it, which meant four things at once:
Net Income equalled EBITDA in every period, a company whose central question is funding showed no
debt, the cash flow statement chosen for its ability to explain the covenant omitted the cost of
the facility, and `financing.py` remained a second source of truth for all of it.

**The covenant figures do not move**, and that is worth stating because the phase 6 spec predicted
they would. `financing.run` already deducts interest and unused fees from its own cash
roll-forward, so the schedule always included the cost of the debt — only the ledger did not.
Posting is therefore purely additive to the ledger and cannot change a figure the schedule
produced. `test_the_covenant_figures_did_not_move` holds that.
"""

from __future__ import annotations

import pandas as pd
import pytest

from bellwether.data import generate
from bellwether.transform import statements

INTEREST = "7000"
FEES = "7010"
REVOLVER = "2500"


@pytest.fixture(scope="module")
def data() -> dict[str, pd.DataFrame]:
    return generate.generate()


# --- 6.1 the entries exist ---------------------------------------------------------------


def test_financing_is_posted_in_every_forecast_combination(data) -> None:
    """6.1 — every version and scenario, not just the operating plan."""
    ledger = data["fact_gl"]
    forecast = ledger[ledger["version_name"] != "Actual"]
    posted = forecast[forecast["account_code"].isin([INTEREST, FEES, REVOLVER])]
    assert not posted.empty
    combinations = forecast.groupby(["version_name", "scenario_name"]).ngroups
    assert posted.groupby(["version_name", "scenario_name"]).ngroups == combinations


def test_posted_interest_and_fees_equal_the_schedule(data) -> None:
    """The ledger is not an approximation of the schedule; it carries the same numbers."""
    ledger, schedule = data["fact_gl"], data["fact_financing_monthly"]
    for account, column in ((INTEREST, "interest_expense"), (FEES, "unused_line_fee")):
        posted = ledger.loc[ledger["account_code"] == account, "amount"].sum()
        expected = schedule[column].sum()
        assert abs(posted - expected) < 0.01, account


# --- 6.2 double entry survives ------------------------------------------------------------


def test_the_trial_balance_still_nets_to_zero(data) -> None:
    """6.2 — the existing check, unamended.

    It passed before because the entries were absent. Passing now means they balance.
    """
    frame = data["fact_gl"].copy()
    frame["period"] = pd.to_datetime(frame["date"]).dt.to_period("M").astype(str)
    worst = frame.groupby(["version_name", "scenario_name", "period"])["amount"].sum().abs().max()
    assert worst < 0.01


# --- 6.3 net income is no longer EBITDA ---------------------------------------------------


def test_net_income_differs_from_ebitda_where_the_facility_was_used(data) -> None:
    """6.3 — the metric was structurally zero, so the measure existed and always said nothing."""
    series = statements.metric_series(data["fact_gl"], data["dim_gl_account"])
    below_the_line = series["Other Income and Expense"]
    assert below_the_line.sum() > 0, "no financing cost reached the P&L"
    differing = (series["EBITDA"] - series["Net Income"]).abs() > 0.01
    assert differing.sum() > len(series) // 2, "too few periods carry a financing cost"
    # And where nothing was drawn and no fee accrued, they should still agree.
    assert (below_the_line[~differing].abs() < 0.01).all()


# --- 6.4 the balance sheet carries the liability ------------------------------------------


def test_the_revolver_balance_equals_the_drawn_balance_every_month(data) -> None:
    """6.4 — month by month, per combination, not just at the end.

    This is the assertion that makes the ledger and the schedule one source rather than two.
    """
    ledger, schedule = data["fact_gl"], data["fact_financing_monthly"]
    frame = ledger[ledger["account_code"] == REVOLVER].copy()
    frame["month"] = pd.to_datetime(frame["date"]).dt.to_period("M").dt.to_timestamp()
    movements = frame.groupby(["version_name", "scenario_name", "month"], as_index=False)[
        "amount"
    ].sum()

    # The grid is completed before cumulating. A month with no movement has no posting, so
    # joining on postings alone silently drops it — and a balance that is only checked in the
    # months it changed is not a balance that has been checked.
    grid = schedule[["version_name", "scenario_name", "month"]].copy()
    grid["month"] = pd.to_datetime(grid["month"])
    merged = grid.merge(
        movements, on=["version_name", "scenario_name", "month"], how="left"
    ).fillna({"amount": 0.0})
    merged = merged.sort_values("month")
    merged["drawn"] = -merged.groupby(["version_name", "scenario_name"])["amount"].cumsum()
    merged = merged.merge(
        schedule[["version_name", "scenario_name", "month", "revolver_drawn"]].assign(
            month=lambda f: pd.to_datetime(f["month"])
        ),
        on=["version_name", "scenario_name", "month"],
        how="inner",
    )
    assert len(merged) == len(schedule), (len(merged), len(schedule))
    assert (merged["drawn"] - merged["revolver_drawn"]).abs().max() < 0.01


def test_the_balance_sheet_still_balances(data) -> None:
    check = statements.balance_sheet_check(data["fact_gl"], data["dim_gl_account"])
    assert check["difference"].abs().max() < 0.01


# --- 6.5 the cash flow shows the cost of the facility --------------------------------------


def test_the_cash_flow_interest_line_equals_posted_interest(data) -> None:
    """6.5 — ADR 0018 chose this statement for its ability to explain the covenant."""
    flow = statements.cash_flow(data["fact_gl"], data["dim_gl_account"])
    ledger = data["fact_gl"]
    posted = ledger.loc[ledger["account_code"].isin([INTEREST, FEES]), "amount"].sum()
    assert posted > 0
    assert abs(flow["Interest and financing fees"].sum() - posted) < 0.01


def test_closing_cash_still_ties_to_balance_sheet_cash(data) -> None:
    tie = statements.cash_tie(data["fact_gl"], data["dim_gl_account"])
    assert tie["difference"].abs().max() < 0.01


# --- the claim the spec got wrong -----------------------------------------------------------


def test_the_covenant_figures_did_not_move(data) -> None:
    """The phase 6 spec predicted every covenant figure would move. It was wrong, and the reason
    is worth holding in a test.

    `financing.run` deducts interest and unused fees from its own cash roll-forward, so the
    schedule always priced the debt. The ledger was the only thing that did not. Posting adds
    entries the schedule already assumed, so no figure it produced can change — and if one ever
    does, the schedule and the ledger have diverged and this test should say so.
    """
    verdicts = {row["scenario_name"]: row for _, row in data["_verdicts"].iterrows()}
    assert abs(float(verdicts["Balanced Base"]["minimum_excess_availability"]) - 745_892.12) < 1.0
    assert verdicts["Wholesale Acceleration"]["first_breach_month"].startswith("2028-05")
    assert (
        abs(float(verdicts["DTC Recovery / Margin"]["minimum_excess_availability"]) - 1_181_021.35)
        < 1.0
    )
    assert float(verdicts["Consolidation / Path to Breakeven"]["peak_revolver_drawn"]) == 0.0


def test_the_opening_drawn_balance_seeds_the_first_movement(data) -> None:
    """A movement is a difference, and the first row has nothing to differ from.

    Without seeding, the first month's draw is silently dropped and the revolver balance is
    understated for the whole horizon by that amount.
    """
    from bellwether.transform import forecast_ledger as fl

    schedule = pd.DataFrame(
        {
            "month": pd.to_datetime(["2026-01-01", "2026-02-01"]),
            "interest_expense": [0.0, 0.0],
            "unused_line_fee": [0.0, 0.0],
            "revolver_drawn": [250_000.0, 250_000.0],
        }
    )
    seeded = fl.post_financing(schedule, "Latest Forecast", "Balanced Base", opening_drawn=0.0)
    drawn = -seeded.loc[seeded["account_code"] == REVOLVER, "amount"].sum()
    assert abs(drawn - 250_000.0) < 0.01, "the first month's draw was dropped"
