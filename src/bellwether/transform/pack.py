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
from bellwether.transform import allocation, bridge, claims, commentary, semantic, units

DISCLOSURE = (
    "Northlake, Inc. is an illustrative company. All data is synthetic — no real company, "
    "no real people, no scraped data."
)

CORPORATE = "Unallocated corporate"


@dataclass(frozen=True)
class Exhibit:
    """One numbered exhibit: a table, its title, and why it is in the pack."""

    key: str
    title: str
    why: str
    table: pd.DataFrame
    #: The Excel named range this becomes, for PNG export — criterion 6.27.
    named_range: str
    #: What each column measures, by column name. Declared here because this is where the
    #: figure is composed; a renderer that infers the unit from the value gets zero balances
    #: and empty residuals wrong. See `units.py`.
    units: dict[str, str] = field(default_factory=dict)
    #: The claims ``why`` makes, each verified against the ledger. See `claims.py`.
    claims: tuple = ()


@dataclass(frozen=True)
class Section:
    """One page of the pack."""

    title: str
    lead: str
    exhibits: list[Exhibit] = field(default_factory=list)
    blocks: list[commentary.Block] = field(default_factory=list)
    #: The claims ``lead`` makes. The sentence stays hand-written; the claim inside it is a
    #: predicate `tests/reporting/test_claims.py` evaluates against the data.
    claims: tuple = ()

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
    for channel in (*bridge.CHANNELS, CORPORATE):
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
    year = max(C.ACTUAL_YEARS)
    ladders = _channel_ladder(gl, accounts, year, "Actual")
    rows = []
    for channel in (*bridge.CHANNELS, CORPORATE):
        ladder = ladders[channel]
        rows.append(
            {
                "": channel,
                "Net revenue": ladder["Net Revenue"],
                # `nan`, not zero, when there is no revenue to divide by. The corporate block
                # has none, and printing its margin as 0.0% states a rate the data does not
                # have — the first review of the pack caught exactly that.
                "Contribution margin": units.ratio(ladder["Gross Profit"], ladder["Net Revenue"]),
                "Contribution": ladder["EBITDA"],
            }
        )
    total = ladders["Total"]
    rows.append(
        {
            "": f"FY{year} total",
            "Net revenue": total["Net Revenue"],
            # The blended margin, computed. It was hard-coded to 0.0, which put a wrong number
            # on the headline table of the client-facing artifact.
            "Contribution margin": units.ratio(total["Gross Profit"], total["Net Revenue"]),
            "Contribution": total["EBITDA"],
        }
    )
    return Exhibit(
        key="channel_contribution",
        # Titles label; leads and rationales claim. A title that asserts is a claim nothing
        # checks, and it read as the third statement of the same finding.
        title=f"Channel contribution, FY{year}",
        why=(
            "A brand that shifted toward wholesale and posted a loss invites the opposite "
            "conclusion, so contribution is shown per channel rather than asserted."
        ),
        table=pd.DataFrame(rows),
        named_range="Exhibit_ChannelContribution",
        claims=claims.CHANNEL_CONTRIBUTION,
        units={
            "": units.TEXT,
            "Net revenue": units.MONEY,
            "Contribution margin": units.PERCENT,
            "Contribution": units.MONEY,
        },
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
    # One row per driver, channels across. The long form put six rows and a repeated spread on
    # the page, each row wrapping to three or four lines with its channel name orphaned above
    # its numbers; three rows make the disagreement between drivers visible at a glance, which
    # is the exhibit's entire argument.
    pivot = sensitivity.pivot(index="driver", columns="channel_name", values="allocated_cost")
    rationale = sensitivity.drop_duplicates("driver").set_index("driver")["rationale"]
    table = pd.DataFrame(
        {
            "Allocation driver": pivot.index,
            "Cost to DTC": pivot["DTC"].to_numpy(),
            "Cost to Wholesale": pivot["Wholesale"].to_numpy(),
            "Why it is defensible": rationale.reindex(pivot.index).to_numpy(),
        }
    )
    # One fact about the whole table, so it is stated once in the rationale rather than repeated
    # down a column. It is the same figure for either channel: the cost is fixed, so whatever one
    # channel gains across drivers the other loses.
    spread = float(sensitivity["range_for_channel"].max())
    return Exhibit(
        key="allocation_sensitivity",
        title="What was not allocated, and what the choice would have been worth",
        why=(
            f"Every driver below is defensible and they disagree by {units.money(spread)} on a "
            f"{units.money(supply_chain_cost(gl, accounts, year))} cost, so choosing one "
            "manufactures precision the business does not have. Showing the range answers the "
            "question a sceptical reader is already forming."
        ),
        table=table,
        named_range="Exhibit_AllocationSensitivity",
        units={
            "Allocation driver": units.TEXT,
            "Cost to DTC": units.MONEY,
            "Cost to Wholesale": units.MONEY,
            "Why it is defensible": units.TEXT,
        },
        claims=claims.ALLOCATION_SENSITIVITY,
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
            "Ranked over the whole horizon, the best cumulative EBITDA of the three that grow "
            "is the one that runs out of room. The explanation is entirely in working capital."
        ),
        table=pd.DataFrame(rows).sort_values("Minimum excess availability"),
        named_range="Exhibit_CovenantTrace",
        units={
            "Scenario": units.TEXT,
            "Peak revolver drawn": units.MONEY,
            "Borrowing base at trough": units.MONEY,
            "Minimum excess availability": units.MONEY,
            "Months drawn": units.COUNT,
            "Holds": units.FLAG,
        },
        claims=claims.COVENANT_TRACE,
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
        table=bridge_built.frame().rename(
            columns={"effect": "Cause", "driver": "What moved", "amount": "Effect on gross profit"}
        ),
        named_range="Exhibit_PLBridge",
        units={
            "Cause": units.TEXT,
            "What moved": units.TEXT,
            "Effect on gross profit": units.MONEY,
        },
        claims=claims.PL_BRIDGE,
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
        why=(
            "The only plan that reaches profitability is the one that grows slowest. It is "
            "still a larger company in FY2028 than it is today."
        ),
        table=pd.DataFrame(rows).sort_values(f"FY{final} net revenue", ascending=False),
        named_range="Exhibit_ScenarioComparison",
        units={
            "Scenario": units.TEXT,
            f"FY{final} net revenue": units.MONEY,
            f"FY{final} EBITDA": units.MONEY,
            "EBITDA margin": units.PERCENT,
        },
        claims=claims.SCENARIO_COMPARISON,
    )


#: The five exhibits that get named ranges, for PNG export — decision G-d.
NAMED_RANGES = (
    "Exhibit_ChannelContribution",
    "Exhibit_AllocationSensitivity",
    "Exhibit_CovenantTrace",
    "Exhibit_PLBridge",
    "Exhibit_ScenarioComparison",
)


def evidence(tables: dict[str, pd.DataFrame], star_gl: pd.DataFrame) -> claims.Evidence:
    """What the pack's hand-written claims are checked against.

    Carries the against-budget bridge because one claim is about that exhibit's own content
    rather than about the ledger.
    """
    accounts = tables["dim_gl_account"]
    year = max(C.ACTUAL_YEARS)
    against_budget = bridge.build(
        "Gross Profit",
        quantities(star_gl, accounts, "Budget", year),
        quantities(star_gl, accounts, "Actual", year),
    )
    return claims.Evidence(tables, star_gl, bridge=against_budget)


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
        claims=claims.POSITION,
        # Both FY2025 comparisons, and the bridge that decomposes the budget one, sit together
        # here. They were at the back of the pack behind the conclusion, which asked a reader
        # to accept a decision and then read the evidence for the year it rests on.
        blocks=[
            commentary.block(
                "Year on year", year_on_year, f"FY{year} gross profit", f"FY{year - 1}"
            ),
            commentary.block(
                "Performance against budget",
                against_budget,
                f"FY{year} gross profit",
                "budget",
            ),
        ],
        exhibits=[exhibit_pl_bridge(against_budget)],
    )

    tension = Section(
        title="The tension",
        lead=(
            "Both channels are contribution-positive, so neither is the loss. The whole of it "
            "is a corporate cost base that was built for wholesale and grew with it — "
            "directionally, but not one for one."
        ),
        # The contribution table moved here from Position: the lead makes the claim and the
        # table is the evidence for it, so they belong on the same page rather than three
        # sections apart with the finding stated in both.
        exhibits=[
            exhibit_channel_contribution(star_gl, accounts),
            exhibit_allocation_sensitivity(tables, star_gl, accounts),
        ],
        claims=claims.TENSION,
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
        claims=claims.FUNDING,
    )

    decision = Section(
        title="What follows",
        lead=(
            "Consolidation is the only plan that reaches profitability inside the horizon and "
            "the only one that never draws the facility. It does so on the lowest revenue of "
            "the four, which is the decision in front of the board: growth that the balance "
            "sheet cannot fund, or a smaller company that funds itself."
        ),
        claims=claims.DECISION,
    )

    return [position, tension, funding, decision]
