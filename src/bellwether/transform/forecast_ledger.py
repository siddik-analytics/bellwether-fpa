"""Double-entry forecast ledger — phase 3 D-1, ADR 0014.

Grain: one row per GL account x department x month x version x scenario.

Phase 2 posted only the income-statement side of the forecast, so the forecast trial balance
could not net to zero and `financing.py` had to compute working capital from scenario drivers
instead of reading it from the ledger. That made it a second source of truth for quantities the
ledger should own.

Every journal here balances by construction, using the same ``Journal`` the actuals use — the
point is one posting engine, not two that agree by inspection.
"""

from __future__ import annotations

import pandas as pd

from bellwether.data import config as C
from bellwether.data.ledger import (
    ADVANCES,
    AP,
    AR,
    CASH,
    INVENTORY,
    PPE,
    PROCESSOR,
    Journal,
)

REVOLVER = "2500"
EQUITY = "3000"
CORP = "Executive / Corporate"


def _movement(current: float, previous: float) -> float:
    return current - previous


#: Balance-sheet accounts carried from the actuals into each forecast version and scenario.
OPENING_ACCOUNTS = (CASH, AR, PROCESSOR, INVENTORY, ADVANCES, AP, REVOLVER, EQUITY, PPE)

RETAINED_EARNINGS = "3900"


def post_opening(
    actual_ledger: pd.DataFrame,
    first_month: pd.Timestamp,
    version: str,
    scenario: str,
    as_of: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Carry the actuals' closing balance sheet into a forecast version and scenario.

    A forecast begins from a stated opening position, not from zero. Without this the ledger
    accumulates *movements* rather than balances, so inventory and cash go negative and the
    borrowing base computed from them is meaningless — which is the trap that made deriving
    working capital from the ledger look impossible in phase 2.
    """
    # `as_of` bounds which actuals form the opening position. The FY2025 budget opens from the
    # FY2024 close, not from everything the actuals eventually contain — a budget approved at the
    # end of FY2024 cannot open on a balance sheet that includes the year it is budgeting.
    source = actual_ledger
    if as_of is not None:
        source = source[pd.to_datetime(source["date"]) < as_of]
    balances = (
        source[source["account_code"].isin(OPENING_ACCOUNTS)]
        .groupby("account_code")["amount"]
        .sum()
    )
    legs = [(account, "Finance", float(amount)) for account, amount in balances.items() if amount]
    # Retained earnings absorbs the balancing figure, which is what it is for.
    legs.append((RETAINED_EARNINGS, CORP, -sum(a for _, _, a in legs)))
    j = Journal()
    j.post(first_month, legs, "Opening balance sheet")
    ledger = j.frame()
    ledger["version_name"] = version
    ledger["scenario_name"] = scenario
    return ledger


def post(plan: pd.DataFrame, version: str, scenario: str) -> pd.DataFrame:
    """Post one version x scenario of the monthly forecast as full double entry.

    ``plan`` carries the monthly P&L and the balance-sheet positions the forecast implies —
    receivables, processor receivable, inventory, supplier advances and payables. The movements
    between months are what make the entries balance, so the balance sheet is derived from the
    same rows the P&L is, not asserted alongside it.
    """
    j = Journal()
    rows = plan.sort_values("month").reset_index(drop=True)
    previous = None

    for r in rows.itertuples():
        month = r.month

        # Revenue and the receivable or processor balance it creates.
        j.post(
            month,
            [
                (PROCESSOR, "Marketing / Ecommerce", r.dtc_revenue),
                ("4000", "Marketing / Ecommerce", -r.dtc_revenue),
            ],
            "Forecast DTC revenue",
        )
        j.post(
            month,
            [
                (AR, "Wholesale Sales", r.wholesale_revenue),
                ("4010", "Wholesale Sales", -r.wholesale_revenue),
            ],
            "Forecast wholesale revenue",
        )

        # Cost of sales relieves inventory.
        cogs = r.revenue - r.gross_profit
        j.post(
            month,
            [
                ("5000", "Supply Chain / Operations", cogs),
                (INVENTORY, "Supply Chain / Operations", -cogs),
            ],
            "Forecast COGS",
        )

        # Operating costs settle in cash.
        # Bad debt provisions against the allowance, it does not pay cash — which is how the
        # actuals post it. Posting it to cash here made the forecast and the actuals two
        # different statements and left the cash flow unable to tie in either.
        if r.bad_debt:
            j.post(
                month,
                [("6400", "Finance", r.bad_debt), ("1180", "Finance", -r.bad_debt)],
                "Forecast bad debt",
            )

        for amount, account, department in (
            (r.payment_processing, "6200", "Marketing / Ecommerce"),
            (r.marketing, "6100", "Marketing / Ecommerce"),
            (r.payroll, "6000", CORP),
            (r.fixed_costs, "6350", CORP),
        ):
            if amount:
                j.post(
                    month,
                    [(account, department, amount), (CASH, "Finance", -amount)],
                    "Forecast operating cost",
                )

        # Balance-sheet movements. Purchases are the balancing figure between the inventory
        # position the plan carries and the cost of sales that relieved it — which is what makes
        # payables and supplier advances derivable rather than assumed.
        if previous is not None:
            inventory_movement = _movement(r.inventory, previous.inventory)
            purchases = inventory_movement + cogs
            advances_movement = _movement(r.supplier_advances, previous.supplier_advances)
            payables_movement = _movement(r.accounts_payable, previous.accounts_payable)
            cash_for_purchases = purchases + advances_movement - payables_movement

            j.post(
                month,
                [
                    (INVENTORY, "Supply Chain / Operations", purchases),
                    (ADVANCES, "Supply Chain / Operations", advances_movement),
                    (AP, "Finance", -payables_movement),
                    (CASH, "Finance", -cash_for_purchases),
                ],
                "Forecast inventory purchases",
            )

            collections = r.wholesale_revenue - _movement(r.receivables, previous.receivables)
            j.post(
                month,
                [(CASH, "Finance", collections), (AR, "Wholesale Sales", -collections)],
                "Forecast wholesale collections",
            )

            settled = r.dtc_revenue - _movement(
                r.processor_receivable, previous.processor_receivable
            )
            j.post(
                month,
                [
                    (CASH, "Finance", settled),
                    (PROCESSOR, "Marketing / Ecommerce", -settled),
                ],
                "Forecast processor settlement",
            )

        if r.capex:
            j.post(
                month,
                [(PPE, CORP, r.capex), (CASH, "Finance", -r.capex)],
                "Forecast capex",
            )

        previous = r

    ledger = j.frame()
    ledger["version_name"] = version
    ledger["scenario_name"] = scenario
    return ledger


def post_financing(
    schedule: pd.DataFrame, version: str, scenario: str, opening_drawn: float = 0.0
) -> pd.DataFrame:
    """Post interest, fees and revolver movements from the financing schedule — phase 6 D-1.

    The schedule already **deducts** interest and fees from its own cash roll-forward, so posting
    them does not change the schedule and cannot move a covenant figure. What it changes is the
    ledger, which until now carried none of it: no interest expense, no fee, and no revolver
    liability for a company whose central question is whether it can fund itself.

    ``opening_drawn`` seeds the first month's movement. Without it the first draw is never
    posted, because a movement is a difference and the first row has nothing to differ from.
    """
    j = Journal()
    previous_drawn = opening_drawn
    for r in schedule.sort_values("month").itertuples():
        if r.interest_expense:
            j.post(
                r.month,
                [("7000", "Finance", r.interest_expense), (CASH, "Finance", -r.interest_expense)],
                "Forecast interest",
            )
        if r.unused_line_fee:
            j.post(
                r.month,
                [("7010", "Finance", r.unused_line_fee), (CASH, "Finance", -r.unused_line_fee)],
                "Forecast unused line fee",
            )
        if previous_drawn is not None:
            draw = r.revolver_drawn - previous_drawn
            if abs(draw) > 0.005:
                j.post(
                    r.month,
                    [(CASH, "Finance", draw), (REVOLVER, "Finance", -draw)],
                    "Forecast revolver movement",
                )
        previous_drawn = r.revolver_drawn

    ledger = j.frame()
    if ledger.empty:
        return ledger
    ledger["version_name"] = version
    ledger["scenario_name"] = scenario
    return ledger


def working_capital_from_ledger(ledger: pd.DataFrame) -> pd.DataFrame:
    """Derive receivables, inventory and payables **from the ledger** — criterion 3.3.

    This is the function that removes ``financing.py``'s second source of truth: once the
    forecast balances, the borrowing base can be computed from posted balances rather than from
    the drivers that produced them.
    """
    balance_accounts = {
        AR: "receivables",
        PROCESSOR: "processor_receivable",
        INVENTORY: "inventory",
        ADVANCES: "supplier_advances",
        AP: "accounts_payable",
        CASH: "cash",
    }
    frame = ledger[ledger["account_code"].isin(balance_accounts)].copy()
    frame["balance_line"] = frame["account_code"].map(balance_accounts)
    frame["month"] = pd.to_datetime(frame["date"]).dt.to_period("M").dt.to_timestamp()
    grouped = frame.groupby(
        ["version_name", "scenario_name", "balance_line", "month"], as_index=False
    )["amount"].sum()
    grouped["balance"] = grouped.groupby(["version_name", "scenario_name", "balance_line"])[
        "amount"
    ].cumsum()
    return grouped.pivot_table(
        index=["version_name", "scenario_name", "month"],
        columns="balance_line",
        values="balance",
    ).reset_index()


def trial_balance(ledger: pd.DataFrame) -> pd.DataFrame:
    """Criterion 3.1 — zero for every period of every version and scenario."""
    frame = ledger.copy()
    frame["period"] = pd.to_datetime(frame["date"]).dt.to_period("M").astype(str)
    return frame.groupby(["version_name", "scenario_name", "period"], as_index=False)[
        "amount"
    ].sum()


__all__ = [
    "C",
    "post",
    "post_financing",
    "trial_balance",
    "working_capital_from_ledger",
]
