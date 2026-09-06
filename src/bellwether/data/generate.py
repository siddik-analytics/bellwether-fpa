"""Orchestration: build the whole Northlake dataset from one seed.

The order is a dependency order, not a preference. Dimensions before facts, actuals before
forecast, and the ledger last because it consumes everything else.
"""

from __future__ import annotations

import logging
import pathlib

import numpy as np
import pandas as pd

from bellwether.data import actuals, dimensions, financing, forecast, stockouts, writer
from bellwether.data import config as C
from bellwether.data import inventory as inventory_mod
from bellwether.data import ledger as ledger_mod

log = logging.getLogger("bellwether.data")


def generate(seed: int = C.SEED) -> dict[str, pd.DataFrame]:
    """Produce every table the data contract declares."""
    rng = np.random.default_rng(seed)
    dims = dimensions.build_all(rng)
    products = dims["dim_product"]
    spine = dims["dim_date"]
    dates = pd.DatetimeIndex(spine["date"])
    actual_dates = dates[dates.year <= max(C.ACTUAL_YEARS)]
    landed = inventory_mod.landed_cost_series(products, actual_dates)

    # --- actuals, at transaction grain ------------------------------------------------
    dtc_demand, customers = actuals.generate_dtc(products, spine, rng, C.DEMAND_GROSS_UP)
    wholesale = actuals.generate_wholesale(
        products, dims["dim_wholesale_account"], spine, rng, C.DEMAND_GROSS_UP
    )
    returns = actuals.generate_returns(dtc_demand, wholesale, rng)

    demand = inventory_mod.daily_demand(dtc_demand, wholesale, products, actual_dates)
    inv, purchase_orders, suppressed = inventory_mod._metrics(
        products,
        dims["dim_supplier"],
        demand,
        actual_dates,
        returns,
        seed,
        C.INVENTORY_WOS_SCALE,
        {"A": C.INVENTORY_CLASS_A_SAFETY_MULTIPLIER, "B": 1.0, "C": 1.0},
        landed,
    )[:3]

    suppressed = stockouts.split_suppressed(suppressed)
    dtc, suppressed_lines = stockouts.apply_to_dtc(dtc_demand, suppressed, rng)
    dtc = dtc[dtc["fiscal_year"] <= max(C.ACTUAL_YEARS)].reset_index(drop=True)
    returns = actuals.generate_returns(dtc, wholesale, np.random.default_rng(seed + 1))

    ledger = ledger_mod.build(
        dtc, wholesale, returns, inv, purchase_orders, products, spine, landed, actual_dates
    )

    # --- forecast, at monthly grain ----------------------------------------------------
    cash_rows = ledger[ledger["account_code"] == ledger_mod.CASH]
    opening_cash = float(cash_rows["amount"].sum())
    revolver_rows = ledger[ledger["account_code"] == ledger_mod.REVOLVER]
    opening_drawn = float(-revolver_rows["amount"].sum())
    closing_revenue = float(C.ACTUALS[max(C.ACTUAL_YEARS)].revenue)

    plan, schedule, verdicts = forecast.build(
        closing_revenue, max(opening_cash, C.MIN_CASH_POLICY), max(opening_drawn, 0.0)
    )
    forecast_ledger = forecast.to_ledger(plan)
    full_ledger = pd.concat([ledger, forecast_ledger], ignore_index=True)

    tables = {
        **dims,
        "dim_customer": customers,
        "fact_dtc_order_line": dtc,
        "fact_dtc_suppressed_demand": suppressed_lines,
        "fact_wholesale_invoice_line": wholesale,
        "fact_return_line": returns,
        "fact_inventory_daily": inv,
        "fact_purchase_order_line": purchase_orders,
        "fact_stockout": suppressed,
        "fact_gl": full_ledger,
        "fact_forecast_monthly": plan,
        "fact_financing_monthly": schedule,
    }
    tables["_verdicts"] = pd.DataFrame(
        [{"scenario_name": k, **{kk: str(vv) for kk, vv in v.items()}} for k, v in verdicts.items()]
    )
    return tables


def run(data_dir: pathlib.Path | None = None, seed: int = C.SEED) -> dict[str, int]:
    """Generate and write. Returns row counts per table."""
    from bellwether.paths import DATA_DIR

    tables = generate(seed)
    counts = writer.write(tables, data_dir or DATA_DIR)
    for name in sorted(counts):
        log.info("  %-32s %9s rows", name, f"{counts[name]:,}")
    return counts


__all__ = ["financing", "generate", "run"]
