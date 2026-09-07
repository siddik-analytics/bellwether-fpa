"""The claims the pack's hand-written prose makes, and the checks that they are true.

Every number in the pack is computed and every commentary sentence is derived from the bridge.
The section leads are not. They are hand-written, because an argument — *"the covenant, not
earnings, decides which plan is available"* — is the thing a reader is paying for, and generating
it would produce exactly the templated prose `commentary.py` exists to avoid.

But a hand-written sentence asserts facts, and the figures in this project have moved repeatedly.
"Consolidation is the only plan that reaches profitability" was true when it was written and
nothing forced it to stay true. So the sentence stays hand-written and **the claim inside it
becomes a predicate**: exactly one scenario reaches breakeven inside the horizon, and it is that
one.

Three rules, enforced by `tests/reporting/test_claims.py`:

1. **Every sentence of every lead is covered by a claim** whose `sentence` fragment is a
   substring of it. Adding a sentence without a claim fails the coverage test.
2. **A sentence that states a fact must be `verified`, not `framing`.** A sentence carrying a
   digit or a quantifier — only, never, every, highest, lowest, neither — cannot be recorded as
   rhetoric. That is the route by which an unchecked claim would get in, and it is closed.
3. **The claims must be able to fail.** ADR 0022's negative control: perturbing the data flips
   them, and a claim that cannot flip is verifying nothing.

The checks compute their own figures from the ledger rather than calling `pack`'s helpers. A
claim that reused the pack's arithmetic would be checking the pack against itself, which is the
failure ADR 0022 is about, so the duplication here is deliberate.

Writing this found two false sentences. See ADR 0024.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from bellwether.data import config as C
from bellwether.transform import bridge as bridge_mod
from bellwether.transform import semantic

#: A raise is "roughly breakeven" if the year's EBITDA margin is inside this band. Stated as a
#: number because "roughly" in a board pack has to mean something a reader can check.
BREAKEVEN_BAND = 0.05

#: Growth "one for one" would be a ratio of 1. Outside this band the two grew together but not
#: proportionally, which is the weaker and accurate claim the tension section makes.
ONE_FOR_ONE = (0.90, 1.10)

CORPORATE = "Unallocated corporate"
CONSOLIDATION = "Consolidation / Path to Breakeven"


@dataclass(frozen=True)
class Verdict:
    """Whether a claim held, and the numbers behind the answer either way."""

    holds: bool
    detail: str


@dataclass(frozen=True)
class Claim:
    """One assertion a hand-written sentence makes.

    ``sentence`` is the fragment of prose being verified, verbatim, so the coverage test can find
    which sentence each claim belongs to. ``kind`` is ``verified`` or ``framing``; framing is for
    sentences that state no fact, and rule 2 above stops it being used for ones that do.
    """

    sentence: str
    kind: str
    check: Callable[[Evidence], Verdict] | None = None

    def verdict(self, evidence: Evidence) -> Verdict:
        if self.kind == "framing" or self.check is None:
            return Verdict(True, "framing — states no checkable fact")
        return self.check(evidence)


def figure(label: str) -> Callable[[Callable[[Evidence], Verdict]], Claim]:
    """A claim about a figure the pack *renders* rather than a sentence it writes.

    A wrong number in a table reaches the reader exactly as a wrong sentence does, and the pack's
    first review found one: the contribution table's total row printed a 0.0% margin where the
    blended rate is 43.6%. Prose coverage could never have caught it, because no prose said it.
    """

    def wrap(check: Callable[[Evidence], Verdict]) -> Claim:
        return Claim(sentence=label, kind="figure", check=check)

    return wrap


def framing(sentence: str) -> Claim:
    """A sentence that argues rather than asserts. Recorded, not checked."""
    return Claim(sentence=sentence, kind="framing")


def verified(sentence: str) -> Callable[[Callable[[Evidence], Verdict]], Claim]:
    def wrap(check: Callable[[Evidence], Verdict]) -> Claim:
        return Claim(sentence=sentence, kind="verified", check=check)

    return wrap


class Evidence:
    """The figures the claims are checked against, computed from the ledger."""

    def __init__(
        self,
        tables: dict[str, pd.DataFrame],
        gl: pd.DataFrame,
        bridge: bridge_mod.Bridge | None = None,
    ) -> None:
        self.tables = tables
        self.accounts = tables["dim_gl_account"]
        self.gl = gl.assign(_year=pd.to_datetime(gl["date"]).dt.year)
        self.last_actual = max(C.ACTUAL_YEARS)
        self.horizon = max(C.FORECAST_YEARS)
        #: The against-budget bridge the pack built. One claim is about the exhibit's own
        #: content rather than about the ledger, so it needs the object the pack rendered.
        self.bridge = bridge

    @functools.cache  # noqa: B019 — one Evidence per comparison, so this is memoisation not a leak
    def actual(self, year: int, channel: str | None = None) -> dict[str, float]:
        frame = self.gl[(self.gl["version_name"] == "Actual") & (self.gl["_year"] == year)]
        if channel is not None:
            frame = frame[frame["channel_allocation"] == channel]
        return semantic.evaluate_ladder(frame, self.accounts)

    @functools.cache  # noqa: B019
    def forecast(self, scenario: str, year: int | None = None) -> dict[str, float]:
        """A scenario's ladder, for one year or cumulatively across the horizon."""
        frame = self.gl[
            (self.gl["version_name"] == "Latest Forecast") & (self.gl["scenario_name"] == scenario)
        ]
        if year is not None:
            frame = frame[frame["_year"] == year]
        return semantic.evaluate_ladder(frame, self.accounts)

    @functools.cache  # noqa: B019
    def scenarios(self) -> tuple[str, ...]:
        latest = self.gl[self.gl["version_name"] == "Latest Forecast"]
        return tuple(sorted(latest["scenario_name"].unique()))

    @functools.cache  # noqa: B019
    def financing(self, scenario: str) -> dict[str, float]:
        schedule = self.tables["fact_financing_monthly"]
        group = schedule[
            (schedule["version_name"] == "Latest Forecast")
            & (schedule["scenario_name"] == scenario)
        ]
        return {
            "peak_drawn": float(group["revolver_drawn"].max()),
            "min_excess": float(group["excess_availability"].min()),
            "breaches": bool(group["covenant_breached"].any()),
        }

    @functools.cache  # noqa: B019
    def allocation_sensitivity(self) -> pd.DataFrame:
        """C-1's grid, assembled here rather than taken from the exhibit it verifies."""
        from bellwether.transform import allocation

        year = self.last_actual
        dtc = self.tables["fact_dtc_order_line"]
        wholesale = self.tables["fact_wholesale_invoice_line"]
        dtc = dtc[dtc["fiscal_year"] == year]
        wholesale = wholesale[wholesale["fiscal_year"] == year]
        cost = semantic.BASE["Operating Expense"].evaluate(
            self.gl[
                (self.gl["version_name"] == "Actual")
                & (self.gl["_year"] == year)
                & (self.gl["department_name"] == "Supply Chain / Operations")
            ],
            self.accounts,
        )
        return allocation.supply_chain_sensitivity(
            units_by_channel={
                "DTC": float(dtc["quantity"].sum()),
                "Wholesale": float(wholesale["units"].sum()),
            },
            revenue_by_channel={
                "DTC": float(dtc["net_merchandise_value"].sum()),
                "Wholesale": float(wholesale["net_revenue"].sum()),
            },
            lines_by_channel={"DTC": float(len(dtc)), "Wholesale": float(len(wholesale))},
            supply_chain_cost=float(cost),
        )

    @functools.cache  # noqa: B019
    def exhibit(self, key: str) -> pd.DataFrame:
        """One exhibit's table as the pack renders it.

        A figure claim is about the artifact's own content, so it reads the artifact. What it
        compares against is computed here, from the ledger, so the two sides stay independent.
        """
        from bellwether.transform import pack

        for section in pack.compose(self.tables, self.gl):
            for exhibit in section.exhibits:
                if exhibit.key == key:
                    return exhibit.table
        raise KeyError(key)

    @functools.cache  # noqa: B019
    def budget(self, year: int) -> dict[str, float]:
        frame = self.gl[(self.gl["version_name"] == "Budget") & (self.gl["_year"] == year)]
        return semantic.evaluate_ladder(frame, self.accounts)

    @functools.cache  # noqa: B019
    def working_capital(self, scenario: str) -> float:
        """Peak receivables and inventory, as the borrowing base measures them."""
        schedule = self.tables["fact_financing_monthly"]
        group = schedule[
            (schedule["version_name"] == "Latest Forecast")
            & (schedule["scenario_name"] == scenario)
        ]
        return float((group["eligible_ar"] + group["eligible_inventory"]).max())

    def profitable_scenarios(self) -> list[str]:
        """Those reaching a positive EBITDA in any year inside the horizon."""
        return [
            s
            for s in self.scenarios()
            if any(self.forecast(s, y)["EBITDA"] > 0 for y in C.FORECAST_YEARS)
        ]

    def undrawn_scenarios(self) -> list[str]:
        return [s for s in self.scenarios() if self.financing(s)["peak_drawn"] == 0]

    def breaching_scenarios(self) -> list[str]:
        return [s for s in self.scenarios() if self.financing(s)["breaches"]]

    def growing_scenarios(self) -> list[str]:
        """Every plan but the smallest — the three the covenant section compares."""
        by_revenue = sorted(self.scenarios(), key=lambda s: self.forecast(s)["Net Revenue"])
        return sorted(by_revenue[1:])

    @staticmethod
    def money(amount: float) -> str:
        return f"{amount:,.0f}"


# --- Position ----------------------------------------------------------------------------------


@verified("of net revenue and an EBITDA loss of")
def _closed_the_year_at_a_loss(e: Evidence) -> Verdict:
    ladder = e.actual(e.last_actual)
    return Verdict(
        ladder["EBITDA"] < 0,
        f"FY{e.last_actual} EBITDA {e.money(ladder['EBITDA'])} on net revenue "
        f"{e.money(ladder['Net Revenue'])}",
    )


@verified("in June 2024")
def _the_raise_landed_in_june_2024(e: Evidence) -> Verdict:
    date = C.EQUITY_RAISE_DATE
    equity = set(e.accounts.loc[e.accounts["account_type"] == "equity", "account_code"])
    posted = e.gl[
        (e.gl["version_name"] == "Actual")
        & (pd.to_datetime(e.gl["date"]).dt.to_period("M") == pd.Period("2024-06", "M"))
        & (e.gl["account_code"].isin(equity))
    ]
    raised = -float(posted["amount"].sum())
    return Verdict(
        (date.year, date.month) == (2024, 6) and abs(raised - C.EQUITY_RAISE) < 0.01,
        f"EQUITY_RAISE_DATE {date.isoformat()}, {e.money(raised)} posted to equity in 2024-06",
    )


@verified("at roughly breakeven")
def _the_raise_was_at_roughly_breakeven(e: Evidence) -> Verdict:
    ladder = e.actual(C.EQUITY_RAISE_DATE.year)
    margin = ladder["EBITDA"] / ladder["Net Revenue"]
    return Verdict(
        abs(margin) < BREAKEVEN_BAND,
        f"FY{C.EQUITY_RAISE_DATE.year} EBITDA margin {margin:.1%}, band ±{BREAKEVEN_BAND:.0%}",
    )


@verified("on a wholesale growth story")
def _wholesale_was_the_growth(e: Evidence) -> Verdict:
    first, last = min(C.ACTUAL_YEARS), e.last_actual
    growth = {
        channel: e.actual(last, channel)["Net Revenue"] / e.actual(first, channel)["Net Revenue"]
        for channel in bridge_mod.CHANNELS
    }
    return Verdict(
        growth["Wholesale"] > growth["DTC"],
        f"FY{first} to FY{last}: wholesale x{growth['Wholesale']:.2f}, DTC x{growth['DTC']:.2f}",
    )


POSITION = (
    _closed_the_year_at_a_loss,
    _the_raise_landed_in_june_2024,
    _the_raise_was_at_roughly_breakeven,
    _wholesale_was_the_growth,
)


# --- The tension -------------------------------------------------------------------------------


@verified("Both channels are contribution-positive, so neither is the loss")
def _both_channels_contribute(e: Evidence) -> Verdict:
    contributions = {c: e.actual(e.last_actual, c)["EBITDA"] for c in bridge_mod.CHANNELS}
    total = e.actual(e.last_actual)["EBITDA"]
    return Verdict(
        all(v > 0 for v in contributions.values()) and total < 0,
        ", ".join(f"{c} {e.money(v)}" for c, v in contributions.items())
        + f"; total {e.money(total)}",
    )


@verified("The whole of it is a corporate cost base")
def _the_block_exceeds_the_loss(e: Evidence) -> Verdict:
    block = e.actual(e.last_actual, CORPORATE)["EBITDA"]
    total = e.actual(e.last_actual)["EBITDA"]
    return Verdict(
        block < 0 and abs(block) > abs(total),
        f"corporate block {e.money(block)} against a total loss of {e.money(total)}",
    )


@verified("grew with it — directionally, but not one for one")
def _the_block_grew_with_wholesale_but_not_proportionally(e: Evidence) -> Verdict:
    first, last = min(C.ACTUAL_YEARS), e.last_actual
    block = abs(e.actual(last, CORPORATE)["EBITDA"]) / abs(e.actual(first, CORPORATE)["EBITDA"])
    wholesale = (
        e.actual(last, "Wholesale")["Net Revenue"] / e.actual(first, "Wholesale")["Net Revenue"]
    )
    ratio = (block - 1) / (wholesale - 1) if wholesale != 1 else float("inf")
    same_direction = (block > 1) == (wholesale > 1)
    return Verdict(
        same_direction and not (ONE_FOR_ONE[0] <= ratio <= ONE_FOR_ONE[1]),
        f"corporate block x{block:.2f}, wholesale revenue x{wholesale:.2f}, "
        f"growth ratio {ratio:.2f}",
    )


TENSION = (
    _both_channels_contribute,
    _the_block_exceeds_the_loss,
    _the_block_grew_with_wholesale_but_not_proportionally,
)


# --- Whether it is fundable --------------------------------------------------------------------


@verified("The covenant, not earnings, decides which plan is available")
def _earnings_and_availability_disagree(e: Evidence) -> Verdict:
    """The claim only means something if the two rankings actually differ."""
    growing = e.growing_scenarios()
    best_earnings = max(growing, key=lambda s: e.forecast(s)["EBITDA"])
    breaching = e.breaching_scenarios()
    return Verdict(
        best_earnings in breaching,
        f"best cumulative EBITDA of the growing plans is {best_earnings} "
        f"({e.money(e.forecast(best_earnings)['EBITDA'])}); breaching {breaching}",
    )


@verified("The plan with the highest revenue is the one that breaches")
def _the_largest_plan_breaches(e: Evidence) -> Verdict:
    largest = max(e.scenarios(), key=lambda s: e.forecast(s)["Net Revenue"])
    breaching = e.breaching_scenarios()
    return Verdict(
        breaching == [largest],
        f"highest revenue {largest} ({e.money(e.forecast(largest)['Net Revenue'])}); "
        f"breaching {breaching or 'none'}",
    )


FUNDING = (_earnings_and_availability_disagree, _the_largest_plan_breaches)


# --- What follows ------------------------------------------------------------------------------


@verified("is the only plan that reaches profitability inside the horizon")
def _one_plan_reaches_breakeven(e: Evidence) -> Verdict:
    profitable = e.profitable_scenarios()
    detail = ", ".join(
        f"{s} FY{e.horizon} {e.money(e.forecast(s, e.horizon)['EBITDA'])}" for s in e.scenarios()
    )
    return Verdict(
        profitable == [CONSOLIDATION],
        f"positive inside the horizon: {profitable or 'none'}; {detail}",
    )


@verified("the only one that never draws the facility")
def _one_plan_never_draws(e: Evidence) -> Verdict:
    undrawn = e.undrawn_scenarios()
    return Verdict(
        undrawn == [CONSOLIDATION],
        "peak drawn: "
        + ", ".join(f"{s} {e.money(e.financing(s)['peak_drawn'])}" for s in e.scenarios()),
    )


@verified("It does so on the lowest revenue of the four")
def _it_is_the_smallest_plan(e: Evidence) -> Verdict:
    smallest = min(e.scenarios(), key=lambda s: e.forecast(s, e.horizon)["Net Revenue"])
    return Verdict(
        smallest == CONSOLIDATION and len(e.scenarios()) == 4,
        f"lowest FY{e.horizon} revenue is {smallest}, of {len(e.scenarios())} scenarios",
    )


DECISION = (
    _one_plan_reaches_breakeven,
    _one_plan_never_draws,
    _it_is_the_smallest_plan,
    framing(
        "which is the decision in front of the board: growth that the balance sheet cannot "
        "fund, or a smaller company that funds itself"
    ),
)


# --- The exhibits ------------------------------------------------------------------------------


@verified("choosing one manufactures precision the business does not have")
def _the_drivers_reverse_the_ranking(e: Evidence) -> Verdict:
    """The sharpest form of C-1: the choice of driver changes which channel looks better.

    A spread measured against an arbitrary threshold would be a number arguing with itself. A
    reversal is a consequence a reader can act on being wrong about.
    """
    table = e.allocation_sensitivity()
    contribution = {c: e.actual(e.last_actual, c)["EBITDA"] for c in bridge_mod.CHANNELS}
    leaders = set()
    for _, group in table.groupby("driver"):
        net = {
            row["channel_name"]: contribution[row["channel_name"]] - row["allocated_cost"]
            for _, row in group.iterrows()
        }
        leaders.add(max(net, key=lambda channel: net[channel]))
    return Verdict(
        len(leaders) > 1,
        f"the leading channel across the {table['driver'].nunique()} drivers is {sorted(leaders)}",
    )


@verified("the best cumulative EBITDA of the three that grow is the one that runs out of room")
def _the_best_growing_plan_runs_out_of_room(e: Evidence) -> Verdict:
    return _earnings_and_availability_disagree.check(e)


@verified("Both show up here as named causes rather than as a single unexplained variance")
def _the_bridge_names_both_causes(e: Evidence) -> Verdict:
    """The supplier increase is a rate effect and the launch shortfall a revenue effect.

    The claim is that both are *named*, so it fails if either falls below materiality or if the
    residual grows larger than the causes it is supposed to have replaced.
    """
    if e.bridge is None:
        return Verdict(False, "no against-budget bridge was supplied")
    named = {effect.name: effect.amount for effect in e.bridge.material_effects}
    residual = abs(e.bridge.residual.amount)
    holds = (
        "Margin rate" in named
        and "Revenue" in named
        and residual < min(abs(v) for v in named.values())
    )
    return Verdict(holds, f"named {sorted(named)}, residual {residual:,.0f}")


@verified("The only plan that reaches profitability is the one that grows slowest")
def _the_profitable_plan_grows_slowest(e: Evidence) -> Verdict:
    growth = {
        s: e.forecast(s, e.horizon)["Net Revenue"]
        / e.forecast(s, min(C.FORECAST_YEARS))["Net Revenue"]
        for s in e.scenarios()
    }
    slowest = min(growth, key=lambda s: growth[s])
    return Verdict(
        e.profitable_scenarios() == [CONSOLIDATION] and slowest == CONSOLIDATION,
        ", ".join(f"{s} x{growth[s]:.2f}" for s in e.scenarios()) + f"; slowest {slowest}",
    )


@verified("A brand that shifted toward wholesale and posted a loss")
def _the_shift_and_the_loss_both_happened(e: Evidence) -> Verdict:
    """The reader's expectation is built on two facts, and both have to be facts."""
    first, last = min(C.ACTUAL_YEARS), e.last_actual
    share = {
        year: e.actual(year, "Wholesale")["Net Revenue"] / e.actual(year)["Net Revenue"]
        for year in (first, last)
    }
    loss = e.actual(last)["EBITDA"]
    return Verdict(
        share[last] > share[first] and loss < 0,
        f"wholesale share {share[first]:.1%} to {share[last]:.1%}, FY{last} EBITDA {e.money(loss)}",
    )


@verified("The explanation is entirely in working capital")
def _working_capital_and_not_earnings_explains_the_breach(e: Evidence) -> Verdict:
    """ "Entirely" is a strong word, so it gets the strong test: earnings must not explain it.

    The breaching plan has to be one that earnings would have ranked well, and it has to carry
    the most working capital of the four. If either half fails, something other than working
    capital is doing the work.
    """
    breaching = e.breaching_scenarios()
    if len(breaching) != 1:
        return Verdict(False, f"breaching {breaching or 'none'} — not a single plan to explain")
    plan = breaching[0]
    worst_earnings = min(e.scenarios(), key=lambda s: e.forecast(s)["EBITDA"])
    heaviest = max(e.scenarios(), key=e.working_capital)
    return Verdict(
        plan != worst_earnings and heaviest == plan,
        f"{plan} breaches; worst cumulative EBITDA is {worst_earnings}; heaviest working "
        f"capital is {heaviest} at {e.money(e.working_capital(plan))}",
    )


@verified("It is still a larger company in FY2028 than it is today")
def _the_smallest_plan_still_grows(e: Evidence) -> Verdict:
    """The plan is the slowest of the four, not a contraction. Those read very differently."""
    horizon = e.forecast(CONSOLIDATION, e.horizon)["Net Revenue"]
    today = e.actual(e.last_actual)["Net Revenue"]
    return Verdict(
        horizon > today,
        f"FY{e.horizon} {e.money(horizon)} against FY{e.last_actual} {e.money(today)}",
    )


@verified("The budget was approved before the April supplier increase and before the")
def _the_budget_predates_both_events(e: Evidence) -> Verdict:
    """The two ways the budget is wrong, each visible in the thing that produced it."""
    budgeted_cost = C.ACTUALS[C.BUDGET_LANDED_COST_YEAR].landed_cost
    realised_cost = C.ACTUALS[C.BUDGET_YEAR].landed_cost
    budgeted_revenue = e.budget(C.BUDGET_YEAR)["Net Revenue"]
    realised_revenue = e.actual(C.BUDGET_YEAR)["Net Revenue"]
    return Verdict(
        budgeted_cost < realised_cost and budgeted_revenue > realised_revenue,
        f"landed cost budgeted {budgeted_cost:.2f} against {realised_cost:.2f} realised; "
        f"revenue budgeted {e.money(budgeted_revenue)} against {e.money(realised_revenue)}",
    )


@verified("Neither channel is the loss")
def _neither_channel_is_the_loss(e: Evidence) -> Verdict:
    return _both_channels_contribute.check(e)


@figure("FY2025 total contribution margin")
def _the_blended_margin_is_the_blended_margin(e: Evidence) -> Verdict:
    """The headline table's total row, against the ledger.

    It was hard-coded to 0.0 and shipped, which is the worst kind of defect in this artifact: a
    number that is wrong rather than a layout that is ugly, on the first table a reader meets.
    """
    table = e.exhibit("channel_contribution")
    year = e.last_actual
    row = table[table[""] == f"FY{year} total"]
    if row.empty:
        return Verdict(False, f"the exhibit has no FY{year} total row")
    rendered = float(row.iloc[0]["Contribution margin"])
    ladder = e.actual(year)
    expected = ladder["Gross Profit"] / ladder["Net Revenue"]
    return Verdict(
        abs(rendered - expected) < 0.0001,
        f"exhibit prints {rendered:.1%}, the ledger gives {expected:.1%}",
    )


@figure("the corporate block's contribution margin")
def _an_undefined_margin_is_not_printed_as_zero(e: Evidence) -> Verdict:
    """No revenue means no rate. Zero percent and no percent are different statements."""
    table = e.exhibit("channel_contribution")
    row = table[table[""] == CORPORATE]
    if row.empty:
        return Verdict(False, "the exhibit has no corporate row")
    margin = row.iloc[0]["Contribution margin"]
    revenue = float(row.iloc[0]["Net revenue"])
    return Verdict(
        bool(pd.isna(margin)) if not revenue else not bool(pd.isna(margin)),
        f"net revenue {e.money(revenue)}, margin rendered as {margin!r}",
    )


CHANNEL_CONTRIBUTION = (
    _neither_channel_is_the_loss,
    _the_shift_and_the_loss_both_happened,
    _the_blended_margin_is_the_blended_margin,
    _an_undefined_margin_is_not_printed_as_zero,
)
ALLOCATION_SENSITIVITY = (
    _the_drivers_reverse_the_ranking,
    framing("Showing the range answers the question a sceptical reader is already forming"),
)
COVENANT_TRACE = (
    _the_best_growing_plan_runs_out_of_room,
    _working_capital_and_not_earnings_explains_the_breach,
)
PL_BRIDGE = (_the_bridge_names_both_causes, _the_budget_predates_both_events)
SCENARIO_COMPARISON = (_the_profitable_plan_grows_slowest, _the_smallest_plan_still_grows)


#: Every claim in the pack, for the coverage and negative-control tests.
ALL = (
    *POSITION,
    *TENSION,
    *FUNDING,
    *DECISION,
    *CHANNEL_CONTRIBUTION,
    *ALLOCATION_SENSITIVITY,
    *COVENANT_TRACE,
    *PL_BRIDGE,
    *SCENARIO_COMPARISON,
)
