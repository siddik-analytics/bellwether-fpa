"""Near-term forecast at product and account grain — contract §8, phase 3 D-d.

Months 1-6 of the forecast carry SKU-level demand and named wholesale accounts, because §8
already commissions "SKU-level inventory planning" and "known wholesale POs" in that band.
Monthly aggregates were under-delivery, not a scoping choice.

This is a **projection of the phase 2 demand model**, not a second generator. It calls
``actuals.generate_dtc`` and ``actuals.generate_wholesale`` with scenario-derived drivers, so
seasonality, SKU concentration, basket shape and account structure are the same code. What
changes is the drivers, and — for Consolidation — which SKUs and accounts are in scope at all.

Because the projection produces **units**, cost of sales is units x effective-dated landed cost.
That is what removes ``GM_CALIBRATION`` (ADR 0015): the forecast no longer estimates margin from
representative per-unit economics, it derives it the way the actuals do.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bellwether.data import actuals, inventory
from bellwether.data import config as C

NEAR_TERM_MONTHS = 6

#: Consolidation prunes the class-C tail and the deepest-discount national accounts (§7.6). Both
#: are represented as scope masks over the existing dimensions rather than as separate logic.
PRUNED_SKU_CLASSES = ("C",)
PRUNED_ACCOUNT_TIERS = ("National",)
PRUNE_SCENARIO = "Consolidation / Path to Breakeven"


def scenario_drivers(scenario: str, year: int, prior_revenue: float) -> C.YearDrivers:
    """Turn a §7.6 scenario driver dict into the same shape the actuals use."""
    d = C.SCENARIOS[scenario][year]
    return C.YearDrivers(
        revenue=prior_revenue * (1 + d["growth"]),
        dtc_share=d["dtc_share"],
        aov=d["aov"],
        landed_cost=d["landed_cost"],
        inventory_turns=d["inventory_turns"],
        headcount=d["headcount"],
        compensation=d["compensation"],
        fixed_costs=d["fixed_costs"],
        marketing_pct=d["marketing_pct"],
        shrink_pct=d["shrink_pct"],
        dso=d["dso"],
        paid_cac=d["paid_cac"],
    )


def scope_masks(
    products: pd.DataFrame, accounts: pd.DataFrame, scenario: str
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Which SKUs and accounts the scenario keeps.

    Returning ``None`` for the unpruned scenarios keeps the fast path identical to the actuals,
    so a scenario that prunes nothing behaves exactly as phase 2 did.
    """
    if scenario != PRUNE_SCENARIO:
        return None, None
    sku_mask = (~products["sku_class"].isin(PRUNED_SKU_CLASSES)).to_numpy().astype(float)
    account_mask = (~accounts["tier"].isin(PRUNED_ACCOUNT_TIERS)).to_numpy().astype(float)
    return sku_mask, account_mask


def project(
    products: pd.DataFrame,
    accounts: pd.DataFrame,
    spine: pd.DataFrame,
    scenario: str,
    prior_revenue: float,
    rng: np.random.Generator,
    year: int = 2026,
) -> dict[str, pd.DataFrame]:
    """Project months 1-6 of ``year`` at transaction grain for one scenario."""
    drivers = scenario_drivers(scenario, year, prior_revenue)
    sku_mask, account_mask = scope_masks(products, accounts, scenario)

    dtc, customers = actuals.generate_dtc(
        products,
        spine,
        rng,
        periods=[(year, drivers)],
        sku_mask=sku_mask,
        first_order_id=90_000_000,
    )
    wholesale = actuals.generate_wholesale(
        products,
        accounts,
        spine,
        rng,
        periods=[(year, drivers)],
        account_mask=account_mask,
        sku_mask=sku_mask,
        first_invoice_id=90_000_000,
    )

    dtc = dtc[pd.to_datetime(dtc["order_date"]).dt.month <= NEAR_TERM_MONTHS].copy()
    wholesale = wholesale[
        pd.to_datetime(wholesale["shipment_date"]).dt.month <= NEAR_TERM_MONTHS
    ].copy()
    for frame in (dtc, wholesale):
        frame["scenario_name"] = scenario
        frame["version_name"] = "Latest Forecast"

    return {"dtc": dtc, "wholesale": wholesale, "customers": customers, "drivers": drivers}


def units_and_cogs(
    dtc: pd.DataFrame, wholesale: pd.DataFrame, products: pd.DataFrame, dates: pd.DatetimeIndex
) -> pd.DataFrame:
    """Units and landed cost of sales by product, channel and month.

    The same derivation the actuals use — units multiplied by the effective-dated landed cost of
    the SKU that shipped — rather than a representative per-unit economic. This is the
    replacement for ``GM_CALIBRATION``.
    """
    landed = inventory.landed_cost_series(products, dates)
    key = {k: i for i, k in enumerate(products["product_key"].to_numpy())}
    row = {d: i for i, d in enumerate(dates)}

    frames = []
    for frame, date_column, unit_column, revenue_column, channel in (
        (dtc, "order_date", "quantity", "net_merchandise_value", "DTC"),
        (wholesale, "shipment_date", "units", "net_revenue", "Wholesale"),
    ):
        if frame.empty:
            continue
        f = frame.copy()
        f["_r"] = pd.to_datetime(f[date_column]).map(row)
        f["_c"] = f["product_key"].map(key)
        f = f.dropna(subset=["_r", "_c"])
        f["landed_cogs"] = landed[f["_r"].astype(int), f["_c"].astype(int)] * f[unit_column]
        f["units"] = f[unit_column]
        f["revenue"] = f[revenue_column]
        f["channel_name"] = channel
        f["month"] = pd.to_datetime(f[date_column]).dt.to_period("M").dt.to_timestamp()
        frames.append(
            f[
                [
                    "month",
                    "product_key",
                    "channel_name",
                    "units",
                    "revenue",
                    "landed_cogs",
                    "scenario_name",
                    "version_name",
                ]
            ]
        )

    if not frames:
        return pd.DataFrame(
            columns=[
                "month",
                "product_key",
                "channel_name",
                "units",
                "revenue",
                "landed_cogs",
                "scenario_name",
                "version_name",
            ]
        )
    out = pd.concat(frames, ignore_index=True)
    return out.groupby(
        ["month", "product_key", "channel_name", "scenario_name", "version_name"],
        as_index=False,
    )[["units", "revenue", "landed_cogs"]].sum()


def product_margin(units: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Product margin by family and channel — the series criterion 3.7 asserts continuity on.

    Product margin excludes delivery costs deliberately: parcel and pick-and-pack are per order
    and wholesale freight is per unit, so neither can be attributed to a SKU without inventing an
    allocation. Those are tested at their own grain instead (criterion 3.7a).
    """
    family = dict(zip(products["product_key"], products["product_family"], strict=True))
    frame = units.copy()
    frame["product_family"] = frame["product_key"].map(family)
    grouped = frame.groupby(
        ["month", "product_family", "channel_name", "scenario_name", "version_name"],
        as_index=False,
    )[["revenue", "landed_cogs", "units"]].sum()
    grouped["product_margin"] = (grouped["revenue"] - grouped["landed_cogs"]) / grouped["revenue"]
    return grouped
