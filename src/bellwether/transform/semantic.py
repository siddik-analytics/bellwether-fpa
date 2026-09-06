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

from bellwether.transform import expressions
from bellwether.transform.allocation import CORPORATE


@dataclass(frozen=True)
class Metric:
    """One metric. Grain, filter, format, derivation and sign convention live with the definition.

    A metric is either **base** — one filter over the ledger — or **derived**, carrying a
    ``derivation`` expression over other metric names. Nothing else computes a metric: the
    scalar ladder, the monthly series, the workbook formulas and the DAX measures are all
    generated from these two fields (ADR 0019).
    """

    name: str
    description: str
    accounts: tuple[str, ...] = ()
    account_types: tuple[str, ...] = ()
    sign: int = 1
    format_string: str = "$#,##0"
    grain: str = "account x department x month x version x scenario"
    #: Arithmetic over other metrics, in DAX reference syntax. Empty for a base metric.
    derivation: str = ""
    display_folder: str = "P&L"
    #: Which direction is favourable. A cost is favourable when it comes in lower, and a
    #: variance measure cannot get its sign right without knowing this — it is a property of
    #: the metric, not an argument at the call site.
    is_cost: bool = False

    @property
    def depends_on(self) -> tuple[str, ...]:
        """The metrics this one reads, derived from the expression rather than restated."""
        return expressions.dependencies(self.derivation) if self.derivation else ()

    def evaluate(self, ledger: pd.DataFrame, accounts: pd.DataFrame) -> float:
        """Base metrics only. A derived metric is evaluated by ``evaluate_ladder``."""
        if self.derivation:
            raise ValueError(f"{self.name} is derived; evaluate it through the ladder")
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
        is_cost=True,
    ),
    "Cost of Sales": Metric(
        "Cost of Sales",
        "Landed cost, outbound shipping and variable fulfilment. Payment processing is excluded "
        "and sits below gross profit — ADR 0004.",
        account_types=("cogs",),
        is_cost=True,
    ),
    "Operating Expense": Metric(
        "Operating Expense",
        "Opex including payment processing",
        account_types=("opex",),
        is_cost=True,
    ),
    "Other Income and Expense": Metric(
        "Other Income and Expense",
        "Interest, financing fees and other non-operating items — everything between EBITDA and "
        "net income.",
        account_types=("other",),
        is_cost=True,
        display_folder="Below the line",
    ),
}

#: Variants. Each carries the arithmetic itself, so nothing downstream has to know that Net
#: Revenue is a subtraction and Gross Margin % is a division — ADR 0019.
DERIVED: dict[str, Metric] = {
    "Net Revenue": Metric(
        "Net Revenue",
        "Gross revenue less contra revenue — the §6.2 gross-to-net ladder",
        derivation="[Gross Revenue] - [Contra Revenue]",
    ),
    "Gross Profit": Metric(
        "Gross Profit",
        "Net revenue less cost of sales",
        derivation="[Net Revenue] - [Cost of Sales]",
    ),
    "Gross Margin %": Metric(
        "Gross Margin %",
        "Gross profit over net revenue",
        format_string="0.0%",
        derivation="DIVIDE([Gross Profit], [Net Revenue])",
    ),
    "Contribution Profit": Metric(
        "Contribution Profit",
        "Gross profit less channel-attributable operating cost. The same arithmetic as EBITDA, "
        "evaluated inside a channel filter: corporate cost is excluded by the §6.7 allocation "
        "mapping, not by a filter written here.",
        derivation="[Gross Profit] - [Operating Expense]",
        display_folder="Channel",
    ),
    "EBITDA": Metric(
        "EBITDA",
        "Net revenue less cost of sales and operating expense, before interest and financing",
        derivation="[Gross Profit] - [Operating Expense]",
    ),
    "EBITDA Margin %": Metric(
        "EBITDA Margin %",
        "EBITDA over net revenue",
        format_string="0.0%",
        derivation="DIVIDE([EBITDA], [Net Revenue])",
    ),
    "Net Income": Metric(
        "Net Income",
        "EBITDA less interest, financing fees and other non-operating items",
        derivation="[EBITDA] - [Other Income and Expense]",
        display_folder="Below the line",
    ),
}

ALL_METRICS: dict[str, Metric] = {**BASE, **DERIVED}


#: Derived metrics in dependency order — computed once, from the definitions themselves.
DERIVATION_ORDER: tuple[str, ...] = tuple(
    expressions.resolution_order({name: m.derivation for name, m in DERIVED.items()})
)

#: The gross-to-net ladder §6.3 requires, in presentation order.
LADDER: tuple[str, ...] = (
    "Gross Revenue",
    "Contra Revenue",
    "Net Revenue",
    "Cost of Sales",
    "Gross Profit",
    "Gross Margin %",
    "Operating Expense",
    "EBITDA",
    "EBITDA Margin %",
)


def derive(values: dict[str, object]) -> dict[str, object]:
    """Extend base metric values with every derived metric, in dependency order.

    Values may be floats or pandas Series — the same expressions serve the scalar ladder and the
    monthly series, which is the property that stopped the ladder existing twice.
    """
    out = dict(values)
    for name in DERIVATION_ORDER:
        out[name] = expressions.evaluate(DERIVED[name].derivation, out)
    return out


def evaluate_ladder(ledger: pd.DataFrame, accounts: pd.DataFrame) -> dict[str, float]:
    """The three-tier hierarchy from §6.3, computed from the ledger alone."""
    base = {name: metric.evaluate(ledger, accounts) for name, metric in BASE.items()}
    return {name: float(value) for name, value in derive(base).items()}


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


def variance_for(metric_name: str, actual: float, comparison: float) -> float:
    """Variance with the direction taken from the metric definition rather than the caller.

    ``is_cost`` used to be an argument, which meant every consumer — including a DAX generator —
    had to keep its own list of which measures are costs. It is a property of the metric.
    """
    return variance(actual, comparison, ALL_METRICS[metric_name].is_cost)


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
                "derivation": m.derivation,
                "is_cost": m.is_cost,
                "is_base": name in BASE,
            }
            for name, m in ALL_METRICS.items()
        ]
    )
