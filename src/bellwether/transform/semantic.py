"""Semantic metric definitions — contract §6, ADR 0007.

Every metric is defined **once**, here, as a testable object carrying its own grain, filter and
format. Power BI consumes these definitions; it does not restate them. A measure that disagrees
between the two is a defect with one obvious side to fix.

Base measures first, then variants built on them. A filter expression repeated across two
definitions is a defect, not a convenience — that repetition is how the two copies start to
drift.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from bellwether.transform.allocation import CORPORATE


@dataclass(frozen=True)
class Metric:
    """One metric. Grain, filter and format live with the definition, never at a call site."""

    name: str
    description: str
    accounts: tuple[str, ...] = ()
    account_types: tuple[str, ...] = ()
    sign: int = 1
    format_string: str = "$#,##0"
    grain: str = "account x department x month x version x scenario"
    depends_on: tuple[str, ...] = ()
    display_folder: str = "P&L"

    def evaluate(self, ledger: pd.DataFrame, accounts: pd.DataFrame) -> float:
        frame = ledger
        if self.account_types:
            typed = accounts.loc[accounts["account_type"].isin(self.account_types), "account_code"]
            frame = frame[frame["account_code"].isin(set(typed))]
        if self.accounts:
            frame = frame[frame["account_code"].isin(self.accounts)]
        return float(frame["amount"].sum()) * self.sign


#: Base measures. Each names the account types it reads rather than repeating a filter.
BASE: dict[str, Metric] = {
    "Gross Revenue": Metric(
        "Gross Revenue",
        "Revenue before contra-revenue deductions",
        account_types=("revenue",),
        sign=-1,
    ),
    "Contra Revenue": Metric(
        "Contra Revenue",
        "Discounts, returns reserves and wholesale deductions. Returns means the reserve booked "
        "at sale, never the utilisation that unwinds it — ADR 0017.",
        account_types=("contra_revenue",),
    ),
    "Cost of Sales": Metric(
        "Cost of Sales",
        "Landed cost, outbound shipping and variable fulfilment. Payment processing is excluded "
        "and sits below gross profit — ADR 0004.",
        account_types=("cogs",),
    ),
    "Operating Expense": Metric(
        "Operating Expense", "Opex including payment processing", account_types=("opex",)
    ),
}

#: Variants, each built from the base measures rather than restating their filters.
DERIVED: dict[str, Metric] = {
    "Net Revenue": Metric(
        "Net Revenue",
        "Gross revenue less contra revenue — the §6.2 gross-to-net ladder",
        depends_on=("Gross Revenue", "Contra Revenue"),
    ),
    "Gross Profit": Metric(
        "Gross Profit",
        "Net revenue less cost of sales",
        depends_on=("Net Revenue", "Cost of Sales"),
    ),
    "Gross Margin %": Metric(
        "Gross Margin %",
        "Gross profit over net revenue",
        format_string="0.0%",
        depends_on=("Gross Profit", "Net Revenue"),
    ),
    "Contribution Profit": Metric(
        "Contribution Profit",
        "Gross profit less channel-attributable operating cost. Corporate is excluded by the "
        "§6.7 allocation mapping, not by a filter written here.",
        depends_on=("Gross Profit", "Operating Expense"),
        display_folder="Channel",
    ),
    "EBITDA": Metric(
        "EBITDA",
        "Contribution profit less unallocated corporate cost",
        depends_on=("Contribution Profit",),
    ),
    "EBITDA Margin %": Metric(
        "EBITDA Margin %",
        "EBITDA over net revenue",
        format_string="0.0%",
        depends_on=("EBITDA", "Net Revenue"),
    ),
}

ALL_METRICS: dict[str, Metric] = {**BASE, **DERIVED}


def evaluate_ladder(ledger: pd.DataFrame, accounts: pd.DataFrame) -> dict[str, float]:
    """The three-tier hierarchy from §6.3, computed from the ledger alone."""
    gross = BASE["Gross Revenue"].evaluate(ledger, accounts)
    contra = BASE["Contra Revenue"].evaluate(ledger, accounts)
    cogs = BASE["Cost of Sales"].evaluate(ledger, accounts)
    opex = BASE["Operating Expense"].evaluate(ledger, accounts)
    net = gross - contra
    gross_profit = net - cogs
    return {
        "Gross Revenue": gross,
        "Contra Revenue": contra,
        "Net Revenue": net,
        "Cost of Sales": cogs,
        "Gross Profit": gross_profit,
        "Gross Margin %": gross_profit / net if net else 0.0,
        "Operating Expense": opex,
        "EBITDA": gross_profit - opex,
        "EBITDA Margin %": (gross_profit - opex) / net if net else 0.0,
    }


def channel_contribution(
    ledger: pd.DataFrame, accounts: pd.DataFrame, units_by_channel: dict[str, float] | None = None
) -> pd.DataFrame:
    """Contribution by channel, with corporate shown once and undivided — ADR 0010.

    The split comes from the ``channel_allocation`` column the star schema resolves through the
    §6.7 mapping table. No conditional in this function decides which cost belongs where, which
    is the property that lets Power BI reproduce it from the same table.
    """
    frame = ledger.merge(accounts[["account_code", "account_type"]], on="account_code", how="left")
    frame = frame[frame["account_type"].notna()]
    # Cost of goods both channels consume is split by the units each shipped — the one
    # allocation §6.7 does make, because units are measured rather than chosen. Everything else
    # is either directly attributable or stays in corporate.
    if units_by_channel:
        total_units = sum(units_by_channel.values())
        shared = frame[frame["channel_allocation"] == "BY_UNITS"]
        if not shared.empty and total_units:
            split = []
            for channel, units in units_by_channel.items():
                part = shared.copy()
                part["amount"] = part["amount"] * (units / total_units)
                part["channel_allocation"] = channel
                split.append(part)
            frame = pd.concat(
                [frame[frame["channel_allocation"] != "BY_UNITS"], *split], ignore_index=True
            )

    rows = []
    for channel, group in frame.groupby("channel_allocation"):
        ladder = evaluate_ladder(group, accounts)
        rows.append({"channel_allocation": channel, **ladder})
    out = pd.DataFrame(rows)
    out["is_corporate"] = out["channel_allocation"] == CORPORATE
    return out


def variance(actual: float, comparison: float, is_cost: bool) -> float:
    """Favourable variance is positive whether the line is revenue or cost — §9 check 24."""
    return (comparison - actual) if is_cost else (actual - comparison)


def decompose(
    actual: float,
    budget: float,
    prior_forecast: float,
    latest_forecast: float,
    is_cost: bool = False,
) -> dict[str, float]:
    """The three decompositions §3.3 requires, each holding one dimension fixed.

    Performance variance is a same-scenario comparison because actuals carry the operating plan
    scenario (ADR 0016) — without that it would cross a dimension boundary the contract says to
    hold fixed, and this function could not be written.
    """
    return {
        "performance_variance": variance(actual, budget, is_cost),
        "forecast_revision": variance(latest_forecast, prior_forecast, is_cost),
        "scenario_difference": variance(latest_forecast, budget, is_cost),
    }


def definitions_frame() -> pd.DataFrame:
    """Every metric as a row — what Power BI's measure table is generated from."""
    return pd.DataFrame(
        [
            {
                "name": m.name,
                "description": m.description,
                "format_string": m.format_string,
                "grain": m.grain,
                "display_folder": m.display_folder,
                "depends_on": ", ".join(m.depends_on),
                "is_base": name in BASE,
            }
            for name, m in ALL_METRICS.items()
        ]
    )
