"""ABL revolver, borrowing base and covenant — contract §6.10, ADR 0008.

Grain: one row per month per version x scenario.

Debt is never a balancing plug. Where the borrowing base is exhausted the model reports the
funding-gap month and the additional capital required rather than drawing beyond availability to
make the balance sheet close.
"""

from __future__ import annotations

import pandas as pd

from bellwether.data import config as C


def borrowing_base(
    receivables: float, inventory_at_cost: float, largest_account_share: float = 0.24
) -> dict[str, float]:
    """Eligibility rules from §6.10, applied in the order the facility documents them."""
    concentration_excess = max(0.0, largest_account_share - C.CONCENTRATION_CAP) * receivables
    eligible_ar = (receivables - concentration_excess) * C.AR_ELIGIBLE_SHARE
    dilution = eligible_ar * C.DILUTION_RESERVE
    ar_advance = (eligible_ar - dilution) * C.AR_ADVANCE_RATE

    eligible_inventory = inventory_at_cost * C.INVENTORY_ELIGIBLE_SHARE
    inventory_advance = min(eligible_inventory * C.INVENTORY_ADVANCE_RATE, C.INVENTORY_SUBLIMIT)

    gross = ar_advance + inventory_advance
    return {
        "eligible_ar": eligible_ar,
        "dilution_reserve": dilution,
        "ar_advance": ar_advance,
        "eligible_inventory": eligible_inventory,
        "inventory_advance": inventory_advance,
        "borrowing_base": min(gross, C.FACILITY),
        "facility_commitment": C.FACILITY,
        "capped_by_facility": gross > C.FACILITY,
    }


def run_from_ledger(
    ledger_balances: pd.DataFrame, ebitda: pd.DataFrame, opening_cash: float, opening_drawn: float
) -> pd.DataFrame:
    """Roll the revolver using balances **posted to the ledger** — criterion 3.3.

    This is what removes the second source of truth. ``ledger_balances`` comes from
    ``transform.forecast_ledger.working_capital_from_ledger``; no working-capital figure here is
    computed from a scenario driver. The facility rules — advance rates, eligibility, the
    covenant test — remain this module's responsibility, and are all it is responsible for.
    """
    frame = ledger_balances.merge(ebitda, on="month", how="left").fillna(0.0)
    frame["working_capital"] = (
        frame["inventory"]
        + frame["receivables"]
        + frame["processor_receivable"]
        + frame["supplier_advances"]
        - frame["accounts_payable"]
    )
    frame["capex"] = C.CAPEX_PER_YEAR / 12
    return run(frame, opening_cash, opening_drawn)


def run(monthly: pd.DataFrame, opening_cash: float, opening_drawn: float) -> pd.DataFrame:
    """Roll the revolver forward month by month.

    ``monthly`` needs columns: month, ebitda, working_capital, receivables, inventory, capex.
    Interest accrues on the **beginning-of-period** balance (ADR 0001), so the schedule is
    acyclic and needs no iteration.
    """
    cash, drawn = opening_cash, opening_drawn
    rows = []
    prev_wc = monthly["working_capital"].iloc[0] if len(monthly) else 0.0

    for r in monthly.itertuples():
        opening_drawn_month = drawn
        interest = opening_drawn_month * (C.SOFR + C.SPREAD) / 12
        unused = max(0.0, C.FACILITY - opening_drawn_month) * C.UNUSED_LINE_FEE / 12

        wc_movement = r.working_capital - prev_wc
        cash_flow = r.ebitda - wc_movement - interest - unused - r.capex + getattr(r, "equity", 0.0)

        base = borrowing_base(r.receivables, r.inventory)

        if cash_flow >= 0:
            repay = min(drawn, cash_flow)
            drawn -= repay
            cash += cash_flow - repay
        else:
            from_cash = min(max(0.0, cash - C.MIN_CASH_POLICY), -cash_flow)
            cash -= from_cash
            drawn += -cash_flow - from_cash

        funding_gap = max(0.0, drawn - base["borrowing_base"])
        drawn = min(drawn, base["borrowing_base"])
        availability = base["borrowing_base"] - drawn

        rows.append(
            {
                "month": r.month,
                "opening_drawn": opening_drawn_month,
                "interest_expense": interest,
                "unused_line_fee": unused,
                "cash_flow": cash_flow,
                # `cash` is deliberately not published — criterion 6.6. It is this roll-forward's
                # own working figure, and it disagrees with the ledger's cash because the two
                # model the accrual-to-cash timing differently. Two published cash figures is a
                # second source of truth for the one quantity the covenant turns on, and nothing
                # downstream read this one. The ledger is the authority; ask it.
                "revolver_drawn": drawn,
                "excess_availability": availability,
                "funding_gap": funding_gap,
                "covenant_breached": availability < C.MIN_EXCESS_AVAILABILITY,
                **base,
            }
        )
        prev_wc = r.working_capital

    return pd.DataFrame(rows)


def covenant_summary(schedule: pd.DataFrame) -> dict:
    """The five separately reported lines from §6.10, reduced to a verdict."""
    breaches = schedule.loc[schedule["covenant_breached"], "month"]
    gaps = schedule.loc[schedule["funding_gap"] > 0, "month"]
    return {
        "minimum_excess_availability": float(schedule["excess_availability"].min()),
        "trough_month": schedule.loc[schedule["excess_availability"].idxmin(), "month"],
        "first_breach_month": breaches.iloc[0] if len(breaches) else None,
        "first_funding_gap_month": gaps.iloc[0] if len(gaps) else None,
        "additional_capital_required": float(schedule["funding_gap"].max()),
        "peak_revolver_drawn": float(schedule["revolver_drawn"].max()),
        "months_drawn": int((schedule["revolver_drawn"] > 1_000).sum()),
        "holds": len(breaches) == 0,
    }
