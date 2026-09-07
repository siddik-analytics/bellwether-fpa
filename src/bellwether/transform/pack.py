"""The board pack, composed headless — criteria 6.20 to 6.25.

Every figure and every sentence in the pack originates here. Excel renders it and exports a PDF;
it composes nothing. That is the same boundary the workbook and Power BI sit behind, and it is
why deleting `excel_stage/` leaves a complete pack definition (criterion 6.25).

The pack is an argument, not a report. The charter is explicit that *"a pack that only reports is
a pack no one needed"*, so the structure is: the position, the tension, the evidence, and what
follows from it. The three carried exhibits in `docs/phases/phase-06-carried.md` are the
evidence, and each was recorded when it was discovered because the reason it matters is clearest
then.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from bellwether.data import config as C
from bellwether.transform import allocation, bridge, commentary, semantic

DISCLOSURE = (
    "Northlake, Inc. is an illustrative company. All data is synthetic — no real company, "
    "no real people, no scraped data."
)


@dataclass(frozen=True)
class Exhibit:
    """One numbered exhibit: a table, its title, and why it is in the pack."""

    key: str
    title: str
    why: str
    table: pd.DataFrame
    #: The Excel named range this becomes, for PNG export — criterion 6.27.
    named_range: str


@dataclass(frozen=True)
class Section:
    """One page of the pack."""

    title: str
    lead: str
    exhibits: list[Exhibit] = field(default_factory=list)
    blocks: list[commentary.Block] = field(default_factory=list)

    @property
    def prose(self) -> str:
        return " ".join([self.lead, *(b.prose for b in self.blocks)])


def _channel_ladder(gl: pd.DataFrame, accounts: pd.DataFrame, year: int, version: str) -> dict:
    frame = gl[
        (gl["version_name"] == version)
        & (pd.to_datetime(gl["date"]).dt.year == year)
        & (gl["scenario_name"] == "Balanced Base")
    ]
    out = {}
    for channel in (*bridge.CHANNELS, "Unallocated corporate"):
        out[channel] = semantic.evaluate_ladder(
            frame[frame["channel_allocation"] == channel], accounts
        )
    out["Total"] = semantic.evaluate_ladder(frame, accounts)
    return out


def quantities(
    gl: pd.DataFrame, accounts: pd.DataFrame, version: str, year: int
) -> bridge.Quantities:
    """One side of a comparison, straight from the posted ledger."""
    ladders = _channel_ladder(gl, accounts, year, version)
    return bridge.quantities_from_ledger(
        f"FY{year} {version.lower()}",
        {c: ladders[c]["Net Revenue"] for c in bridge.CHANNELS},
        {c: ladders[c]["Gross Profit"] for c in bridge.CHANNELS},
        ladders["Unallocated corporate"]["Gross Profit"],
    )


# --- the three carried exhibits ----------------------------------------------------------------


def exhibit_channel_contribution(gl: pd.DataFrame, accounts: pd.DataFrame) -> Exhibit:
    """C-2 — it reverses the conclusion a reader arrives with."""
    ladders = _channel_ladder(gl, accounts, max(C.ACTUAL_YEARS), "Actual")
    rows = []
    for channel in (*bridge.CHANNELS, "Unallocated corporate"):
        ladder = ladders[channel]
        revenue = ladder["Net Revenue"]
        rows.append(
            {
                "": channel,
                "Net revenue": revenue,
                "Contribution margin": ladder["Gross Profit"] / revenue if revenue else 0.0,
                "Contribution": ladder["EBITDA"],
            }
        )
    rows.append(
        {
            "": f"FY{max(C.ACTUAL_YEARS)} total",
            "Net revenue": ladders["Total"]["Net Revenue"],
            "Contribution margin": 0.0,
            "Contribution": ladders["Total"]["EBITDA"],
        }
    )
    return Exhibit(
        key="channel_contribution",
        title="Both channels contribute; the loss is the corporate block",
        why=(
            "A brand that shifted toward wholesale and posted a loss looks like a brand whose "
            "wholesale margin does not cover its costs. Neither channel is the loss."
        ),
        table=pd.DataFrame(rows),
        named_range="Exhibit_ChannelContribution",
    )


SUPPLY_CHAIN_DEPARTMENT = "Supply Chain / Operations"


def supply_chain_cost(gl: pd.DataFrame, accounts: pd.DataFrame, year: int) -> float:
    """The department's own operating cost, from the ledger.

    Derived rather than declared as a constant: the exhibit's whole argument is about how much a
    real number moves under different drivers, so the number itself has to be the real one.
    """
    frame = gl[
        (gl["version_name"] == "Actual")
        & (pd.to_datetime(gl["date"]).dt.year == year)
        & (gl["department_name"] == SUPPLY_CHAIN_DEPARTMENT)
    ]
    return float(semantic.BASE["Operating Expense"].evaluate(frame, accounts))


def exhibit_allocation_sensitivity(
    tables: dict[str, pd.DataFrame], gl: pd.DataFrame, accounts: pd.DataFrame
) -> Exhibit:
    """C-1 — what the pack deliberately did not allocate, and what the choice was worth."""
    year = max(C.ACTUAL_YEARS)
    dtc, wholesale = tables["fact_dtc_order_line"], tables["fact_wholesale_invoice_line"]
    dtc_year = dtc[dtc["fiscal_year"] == year]
    ws_year = wholesale[wholesale["fiscal_year"] == year]
    sensitivity = allocation.supply_chain_sensitivity(
        units_by_channel={
            "DTC": float(dtc_year["quantity"].sum()),
            "Wholesale": float(ws_year["units"].sum()),
        },
        revenue_by_channel={
            "DTC": float(dtc_year["net_merchandise_value"].sum()),
            "Wholesale": float(ws_year["net_revenue"].sum()),
        },
        lines_by_channel={"DTC": float(len(dtc_year)), "Wholesale": float(len(ws_year))},
        supply_chain_cost=supply_chain_cost(gl, accounts, year),
    )
    return Exhibit(
        key="allocation_sensitivity",
        title="What was not allocated, and what the choice would have been worth",
        why=(
            "Every driver below is defensible and they disagree by enough that choosing one "
            "manufactures precision the business does not have. Showing the range answers the "
            "question a sceptical reader is already forming."
        ),
        table=sensitivity,
        named_range="Exhibit_AllocationSensitivity",
    )


def exhibit_covenant_trace(tables: dict[str, pd.DataFrame]) -> Exhibit:
    """C-3 — the only exhibit that explains why the strongest plan is the one that breaches."""
    schedule = tables["fact_financing_monthly"]
    latest = schedule[schedule["version_name"] == "Latest Forecast"]
    rows = []
    for scenario, group in latest.groupby("scenario_name"):
        trough = group.loc[group["excess_availability"].idxmin()]
        rows.append(
            {
                "Scenario": scenario,
                "Peak revolver drawn": float(group["revolver_drawn"].max()),
                "Borrowing base at trough": float(trough["borrowing_base"]),
                "Minimum excess availability": float(group["excess_availability"].min()),
                "Months drawn": int((group["revolver_drawn"] > 1_000).sum()),
                "Holds": not bool(group["covenant_breached"].any()),
            }
        )
    return Exhibit(
        key="covenant_trace",
        title="EBITDA to borrowing base to covenant",
        why=(
            "The scenario with the highest revenue and the best EBITDA of the three that grow "
            "is the one that runs out of room. The explanation is entirely in working capital."
        ),
        table=pd.DataFrame(rows).sort_values("Minimum excess availability"),
        named_range="Exhibit_CovenantTrace",
    )


def exhibit_pl_bridge(bridge_built: bridge.Bridge) -> Exhibit:
    """The bridge itself, as the reader sees it — one row per named cause."""
    return Exhibit(
        key="pl_bridge",
        title="FY2025 gross profit against budget, by cause",
        why=(
            "The budget was approved before the April supplier increase and before the "
            "food-storage launch missed. Both show up here as named causes rather than as a "
            "single unexplained variance."
        ),
        table=bridge_built.frame(),
        named_range="Exhibit_PLBridge",
    )


def exhibit_scenario_comparison(gl: pd.DataFrame, accounts: pd.DataFrame) -> Exhibit:
    """Four strategic alternatives on two axes."""
    final = max(C.FORECAST_YEARS)
    frame = gl[
        (gl["version_name"] == "Latest Forecast") & (pd.to_datetime(gl["date"]).dt.year == final)
    ]
    rows = []
    for scenario, group in frame.groupby("scenario_name"):
        ladder = semantic.evaluate_ladder(group, accounts)
        rows.append(
            {
                "Scenario": scenario,
                f"FY{final} net revenue": ladder["Net Revenue"],
                f"FY{final} EBITDA": ladder["EBITDA"],
                "EBITDA margin": ladder["EBITDA Margin %"],
            }
        )
    return Exhibit(
        key="scenario_comparison",
        title="Four scenarios, on two axes",
        why="The only plan that reaches profitability is the one that shrinks.",
        table=pd.DataFrame(rows).sort_values(f"FY{final} net revenue", ascending=False),
        named_range="Exhibit_ScenarioComparison",
    )


#: The five exhibits that get named ranges, for PNG export — decision G-d.
NAMED_RANGES = (
    "Exhibit_ChannelContribution",
    "Exhibit_AllocationSensitivity",
    "Exhibit_CovenantTrace",
    "Exhibit_PLBridge",
    "Exhibit_ScenarioComparison",
)


def compose(tables: dict[str, pd.DataFrame], star_gl: pd.DataFrame) -> list[Section]:
    """The whole pack: position, tension, evidence, and what follows."""
    accounts = tables["dim_gl_account"]
    year = max(C.ACTUAL_YEARS)

    budget_side = quantities(star_gl, accounts, "Budget", year)
    actual_side = quantities(star_gl, accounts, "Actual", year)
    prior_side = quantities(star_gl, accounts, "Actual", year - 1)

    against_budget = bridge.build("Gross Profit", budget_side, actual_side)
    year_on_year = bridge.build("Gross Profit", prior_side, actual_side)

    ladders = _channel_ladder(star_gl, accounts, year, "Actual")
    total = ladders["Total"]

    position = Section(
        title="Position",
        lead=(
            f"Northlake closed FY{year} on {commentary.money(total['Net Revenue'])} of net "
            f"revenue and an EBITDA loss of {commentary.money(total['EBITDA'])}. It raised "
            f"{commentary.money(C.EQUITY_RAISE)} in June 2024, at roughly breakeven, on a "
            "wholesale growth story."
        ),
        exhibits=[exhibit_channel_contribution(star_gl, accounts)],
        blocks=[
            commentary.block(
                "Performance against budget",
                against_budget,
                f"FY{year} gross profit",
                "budget",
            ),
            commentary.block(
                "Year on year", year_on_year, f"FY{year} gross profit", f"FY{year - 1}"
            ),
        ],
    )

    tension = Section(
        title="The tension",
        lead=(
            "Both channels are contribution-positive, so neither is the loss. The whole of it "
            "is a corporate cost base that was built for wholesale and grew with it — "
            "directionally, but not one for one."
        ),
        exhibits=[exhibit_allocation_sensitivity(tables, star_gl, accounts)],
    )

    funding = Section(
        title="Whether it is fundable",
        lead=(
            "The covenant, not earnings, decides which plan is available. The plan with the "
            "highest revenue is the one that breaches."
        ),
        exhibits=[
            exhibit_covenant_trace(tables),
            exhibit_scenario_comparison(star_gl, accounts),
        ],
    )

    decision = Section(
        title="What follows",
        lead=(
            "Consolidation is the only plan that reaches profitability inside the horizon and "
            "the only one that never draws the facility. It does so on the lowest revenue of "
            "the four, which is the decision in front of the board: growth that the balance "
            "sheet cannot fund, or a smaller company that funds itself."
        ),
        exhibits=[exhibit_pl_bridge(against_budget)],
    )

    return [position, tension, funding, decision]
