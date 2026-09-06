"""Stockout suppression — contract §6.6.

Stockouts are a suppression layer over underlying demand, not weak demand. Both quantities are
carried, so poor availability is never misread as a demand problem.

The direction matters and is easy to get wrong. Demand is grossed up so that revenue lands on
target *after* suppression. Generating on-target revenue and then adding orders back to cover
the shortfall would produce the same top line while erasing the cost of the stockout, which is
the one thing this module exists to represent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bellwether.data import config as C


def split_suppressed(stock: pd.DataFrame) -> pd.DataFrame:
    """Half of suppressed demand is lost, half deferred (§6.6)."""
    out = stock.copy()
    out["lost_units"] = out["suppressed_units"] * C.STOCKOUT_LOST_SHARE
    out["deferred_units"] = out["suppressed_units"] - out["lost_units"]
    return out


def apply_to_dtc(
    dtc: pd.DataFrame, stock: pd.DataFrame, rng: np.random.Generator
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Remove lost demand and re-date deferred demand on DTC order lines.

    Returns ``(realised_lines, suppressed_lines)``. The suppressed frame is retained rather than
    discarded: it is the underlying-demand side of the §6.6 comparison, and check 20 asserts the
    gap between the two.
    """
    if stock.empty:
        return dtc, dtc.iloc[0:0].copy()

    dtc = dtc.reset_index(drop=True)
    key = pd.MultiIndex.from_arrays([dtc["order_date"], dtc["product_key"]])
    lost_by = stock.set_index(["date", "product_key"])["lost_units"]
    defer_by = stock.set_index(["date", "product_key"])["deferred_units"]

    lost_target = pd.Series(lost_by.reindex(key).to_numpy(), index=dtc.index).fillna(0.0)
    defer_target = pd.Series(defer_by.reindex(key).to_numpy(), index=dtc.index).fillna(0.0)

    # Within each (day, SKU) the lines are shuffled and consumed in order, so which lines are
    # suppressed is deterministic under the seed but not correlated with order value.
    order = rng.permutation(len(dtc))
    ranked = dtc.iloc[order].copy()
    ranked["_lost_need"] = lost_target.iloc[order].to_numpy()
    ranked["_defer_need"] = defer_target.iloc[order].to_numpy()
    grp = ranked.groupby([ranked["order_date"], ranked["product_key"]], sort=False)
    cum = grp["quantity"].cumsum()

    is_lost = cum <= ranked["_lost_need"]
    is_deferred = (~is_lost) & (cum <= ranked["_lost_need"] + ranked["_defer_need"])

    suppressed = ranked.loc[is_lost | is_deferred].drop(columns=["_lost_need", "_defer_need"])
    realised = ranked.loc[~is_lost].copy()
    # Deferred demand converts later, when stock is available again.
    shift = is_deferred.loc[realised.index]
    realised.loc[shift, "order_date"] = realised.loc[shift, "order_date"] + pd.Timedelta(days=21)
    realised = realised.drop(columns=["_lost_need", "_defer_need"])
    realised = realised.sort_values(["order_date", "order_id", "line_number"]).reset_index(
        drop=True
    )
    realised["fiscal_year"] = realised["order_date"].dt.year
    return realised, suppressed.reset_index(drop=True)


def hero_gap(demand_units: float, realised_units: float) -> float:
    """The demand-to-realised gap as a share of demand — check 20."""
    return (demand_units - realised_units) / demand_units if demand_units else 0.0
