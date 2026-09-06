"""FY2026-FY2028 forecast — contract §7.6 and §8.

Grain: GL account x department x month x version x scenario.

The forecast is monthly, not transactional. §8 states that months 19-36 do not require
artificial order-line precision, and inventing order lines for 2028 would produce a much larger
dataset that is no more informative.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bellwether.data import config as C
from bellwether.data import financing

#: Version x scenario combinations that actually exist. Budget was approved under the operating
#: plan only; generating the full cross-product would fabricate versions the business never
#: produced.
VERSION_SCENARIOS: list[tuple[str, str]] = [("Budget", "Balanced Base")] + [
    (v, s) for v in ("Prior Forecast", "Latest Forecast") for s in C.SCENARIOS
]


def _unit_economics(d: dict) -> tuple[float, float]:
    """Per-order DTC and per-unit wholesale gross margin, post-return (§7.1)."""
    dtc_rev = d["aov"] * (1 - C.DTC_RETURN_RATE) + C.DTC_SHIPPING_REVENUE_PER_ORDER
    dtc_cost = (
        C.UNITS_PER_ORDER * d["landed_cost"] * (1 - C.DTC_RETURN_RATE * C.DTC_RETURN_RECOVERY)
        + C.DTC_PARCEL_COST
        + C.DTC_FULFILMENT_COST
    )
    ws_rev = C.WS_NET_PRICE_PER_UNIT * (d["landed_cost"] / 15.00) ** 0.35
    ws_cost = (
        d["landed_cost"] * (1 - C.WS_RETURN_RATE * C.WS_RETURN_RECOVERY)
        + ws_rev * C.WS_FREIGHT_PCT_OF_NET
        + C.WS_FULFILMENT_PER_UNIT
    )
    return (dtc_rev - dtc_cost) / dtc_rev, (ws_rev - ws_cost) / ws_rev


#: The generator's landed COGS per revenue dollar runs above what the per-unit economics above
#: imply, because units per revenue dollar rise with the wholesale mix and recovered returns are
#: reshipped. Calibrated to the FY2025 actual so the forecast continues from where actuals end
#: rather than stepping. See ADR 0013.
GM_CALIBRATION = 0.031


def monthly_pl(scenario: str, opening_revenue: float) -> pd.DataFrame:
    """Monthly P&L and working capital for one scenario across the forecast horizon."""
    rows, revenue = [], opening_revenue
    for year in C.FORECAST_YEARS:
        d = C.SCENARIOS[scenario][year]
        revenue *= 1 + d["growth"]
        dtc_annual = revenue * d["dtc_share"]
        ws_annual = revenue - dtc_annual
        dtc_gm, ws_gm = _unit_economics(d)
        blended = d["dtc_share"] * dtc_gm + (1 - d["dtc_share"]) * ws_gm - GM_CALIBRATION

        landed_annual = revenue * (1 - blended) * 0.78
        avg_inventory = landed_annual / d["inventory_turns"]

        for m in range(12):
            month = pd.Timestamp(year, m + 1, 1)
            dtc = dtc_annual * C.DTC_MONTHLY_SEASONALITY[m]
            ws = ws_annual * C.WS_MONTHLY_SEASONALITY[m]
            rev_m = dtc + ws
            # November and December carry a revenue spike and a margin trough together (§7.4).
            season_gm = {10: -0.022, 11: -0.014}.get(m, 0.002)
            gross_profit = rev_m * (blended + season_gm) - avg_inventory * d["shrink_pct"] / 12

            processing = (
                dtc * (1 + C.DTC_SHIPPING_REVENUE_PER_ORDER / d["aov"]) * C.PAYMENT_PROCESSING_PCT
            )
            marketing = rev_m * d["marketing_pct"]
            payroll = d["headcount"] * d["compensation"] / 12
            fixed = d["fixed_costs"] / 12
            bad_debt = ws * C.BAD_DEBT_PCT
            ebitda = gross_profit - processing - marketing - payroll - fixed - bad_debt

            receivables = ws_annual * d["dso"] / 365
            processor = (
                dtc
                * (1 + C.DTC_SHIPPING_REVENUE_PER_ORDER / d["aov"])
                * C.PROCESSOR_SETTLEMENT_DAYS
                / 30.4
            )
            inventory = (
                avg_inventory
                * [0.95, 1.00, 1.05, 1.08, 1.12, 1.15, 1.15, 1.12, 1.05, 0.98, 0.88, 0.87][m]
            )
            advances, payables = inventory * 0.27, inventory * 0.21

            rows.append(
                {
                    "month": month,
                    "scenario_name": scenario,
                    "fiscal_year": year,
                    "dtc_revenue": dtc,
                    "wholesale_revenue": ws,
                    "revenue": rev_m,
                    "gross_profit": gross_profit,
                    "gross_margin": gross_profit / rev_m,
                    "payment_processing": processing,
                    "marketing": marketing,
                    "payroll": payroll,
                    "fixed_costs": fixed,
                    "bad_debt": bad_debt,
                    "ebitda": ebitda,
                    "receivables": receivables,
                    "processor_receivable": processor,
                    "inventory": inventory,
                    "supplier_advances": advances,
                    "accounts_payable": payables,
                    "working_capital": inventory + receivables + processor + advances - payables,
                    "capex": C.CAPEX_PER_YEAR / 12,
                }
            )
    return pd.DataFrame(rows)


def build(
    opening_revenue: float, opening_cash: float, opening_drawn: float
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Forecast every version x scenario that exists, with its financing schedule."""
    pl_frames, fin_frames, verdicts = [], [], {}

    for scenario in C.SCENARIOS:
        pl = monthly_pl(scenario, opening_revenue)
        schedule = financing.run(pl, opening_cash, opening_drawn)
        schedule["scenario_name"] = scenario
        verdicts[scenario] = financing.covenant_summary(schedule)
        fin_frames.append(schedule)

        for version, scen in VERSION_SCENARIOS:
            if scen != scenario:
                continue
            frame = pl.copy()
            frame["version_name"] = version
            # Budget is the plan as approved; the prior forecast is one cycle stale. Neither is
            # the latest view, and the differences are what variance reporting decomposes (§3.3).
            if version == "Budget":
                frame[["revenue", "ebitda"]] *= 1.04
            elif version == "Prior Forecast":
                frame[["revenue", "ebitda"]] *= 1.015
            pl_frames.append(frame)

    return (
        pd.concat(pl_frames, ignore_index=True),
        pd.concat(fin_frames, ignore_index=True),
        verdicts,
    )


def to_ledger(pl: pd.DataFrame) -> pd.DataFrame:
    """Map the monthly forecast onto GL accounts and departments (§8)."""
    mapping = [
        ("dtc_revenue", "4000", "Marketing / Ecommerce", -1),
        ("wholesale_revenue", "4010", "Wholesale Sales", -1),
        ("payment_processing", "6200", "Marketing / Ecommerce", 1),
        ("marketing", "6100", "Marketing / Ecommerce", 1),
        ("payroll", "6000", "Executive / Corporate", 1),
        ("fixed_costs", "6350", "Executive / Corporate", 1),
        ("bad_debt", "6400", "Finance", 1),
    ]
    out = []
    for column, account, department, sign in mapping:
        frame = pl[["month", "version_name", "scenario_name", column]].copy()
        frame = frame.rename(columns={"month": "date", column: "amount"})
        frame["amount"] *= sign
        frame["account_code"] = account
        frame["department_name"] = department
        out.append(frame)
    cogs = pl[["month", "version_name", "scenario_name"]].copy()
    cogs["amount"] = pl["revenue"] - pl["gross_profit"]
    cogs["account_code"] = "5000"
    cogs["department_name"] = "Supply Chain / Operations"
    out.append(cogs.rename(columns={"month": "date"}))
    return pd.concat(out, ignore_index=True)[
        ["date", "account_code", "department_name", "amount", "version_name", "scenario_name"]
    ]


def hero_service_gap(demand_units: np.ndarray, realised_units: np.ndarray) -> float:
    return float((demand_units.sum() - realised_units.sum()) / demand_units.sum())
