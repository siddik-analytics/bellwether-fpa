"""Star schema: conformed dimensions, surrogate keys, and the GL bridge — contract §4, §5.

Two rules hold everywhere here.

**No null foreign keys.** Every dimension carries an explicit "Not applicable" member for facts
that legitimately have no value for it — a wholesale invoice has no customer, a payroll journal
has no product. A null degrades silently in a BI tool; an explicit member is visible and
countable.

**Actuals carry the operating plan scenario** (ADR 0016), not a "Not applicable" member, so
performance variance stays the same-scenario comparison §3.3 defines.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

NOT_APPLICABLE = "Not applicable"
NA_KEY = 0

#: Which conformed dimension each fact joins to. This is the bus matrix, as data — a test
#: asserts the built schema matches it, so the documented matrix cannot drift from the code.
BUS_MATRIX: dict[str, tuple[str, ...]] = {
    "fact_dtc_order_line": (
        "dim_date",
        "dim_product",
        "dim_customer",
        "dim_channel",
        "dim_promotion",
        "dim_version",
        "dim_scenario",
    ),
    "fact_wholesale_invoice_line": (
        "dim_date",
        "dim_product",
        "dim_wholesale_account",
        "dim_channel",
        "dim_version",
        "dim_scenario",
    ),
    "fact_return_line": (
        "dim_date",
        "dim_product",
        "dim_customer",
        "dim_wholesale_account",
        "dim_channel",
    ),
    "fact_inventory_daily": ("dim_date", "dim_product", "dim_location"),
    "fact_purchase_order_line": ("dim_date", "dim_product", "dim_supplier"),
    "fact_stockout": ("dim_date", "dim_product"),
    "fact_gl": (
        "dim_date",
        "dim_gl_account",
        "dim_department",
        "dim_channel",
        "dim_version",
        "dim_scenario",
    ),
    "fact_forecast_monthly": ("dim_date", "dim_channel", "dim_version", "dim_scenario"),
    "fact_financing_monthly": ("dim_date", "dim_scenario"),
}


def add_not_applicable(dimension: pd.DataFrame, key_column: str, label_column: str) -> pd.DataFrame:
    """Prepend the explicit N/A member. Key 0, so a real surrogate key is never zero."""
    if (dimension[key_column] == NA_KEY).any():
        return dimension
    row = {column: pd.NA for column in dimension.columns}
    row[key_column] = NA_KEY
    row[label_column] = NOT_APPLICABLE
    return pd.concat([pd.DataFrame([row]), dimension], ignore_index=True)


def conform_dimensions(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Add N/A members where a fact can legitimately lack a value."""
    out = dict(tables)
    for name, key_column, label_column in (
        ("dim_customer", "customer_key", "acquisition_channel"),
        ("dim_product", "product_key", "sku_code"),
        ("dim_wholesale_account", "account_key", "account_name"),
        ("dim_promotion", "promotion_key", "promotion_name"),
        ("dim_supplier", "supplier_key", "supplier_name"),
        ("dim_location", "location_key", "location_name"),
    ):
        if name in out:
            out[name] = add_not_applicable(out[name], key_column, label_column)
    return out


def attach_channel(fact: pd.DataFrame, channels: pd.DataFrame, channel_name: str) -> pd.DataFrame:
    """Give a single-channel fact its channel key, so one slicer filters across facts."""
    key = int(channels.loc[channels["channel_name"] == channel_name, "channel_key"].iloc[0])
    out = fact.copy()
    out["channel_key"] = np.int32(key)
    return out


def channel_key_for_ledger(
    ledger: pd.DataFrame, mapping: pd.DataFrame, channels: pd.DataFrame
) -> pd.DataFrame:
    """Resolve every ledger row to a channel through the §6.7 allocation mapping.

    Rows the mapping sends to ``BY_UNITS`` are cost of goods both channels consume; they resolve
    to the corporate member here and are split by units in the semantic layer, where the unit
    counts live.
    """
    lookup = channels.set_index("channel_name")["channel_key"].to_dict()
    corporate = lookup["Unallocated corporate"]
    resolved = mapping.set_index(["account_code", "department_name"])["channel_allocation"]
    out = ledger.copy()
    allocation = resolved.reindex(
        pd.MultiIndex.from_arrays([out["account_code"], out["department_name"]])
    ).to_numpy()
    out["channel_allocation"] = pd.Series(allocation, index=out.index).fillna(
        "Unallocated corporate"
    )
    out["channel_key"] = out["channel_allocation"].map(lookup).fillna(corporate).astype("int32")
    return out


def build_gl_bridge(
    ledger: pd.DataFrame, dtc: pd.DataFrame, wholesale: pd.DataFrame
) -> pd.DataFrame:
    """Bridge from a GL revenue posting to the transaction lines behind it — D-c, §5.

    A bridge rather than extra keys on ``fact_gl``. Widening the ledger would break its declared
    grain, and most postings have no single product: a payroll journal, a fixed-cost accrual and
    an interest charge each have none. The bridge carries the relationship only where one exists.

    Grain: one row per (posting date, account, transaction line).
    """
    frames = []
    for frame, account, date_column, id_column, line_column, amount_column in (
        (dtc, "4000", "order_date", "order_id", "line_number", "net_merchandise_value"),
        (wholesale, "4010", "shipment_date", "invoice_id", "line_number", "net_revenue"),
    ):
        if frame.empty:
            continue
        bridge = pd.DataFrame(
            {
                "date": pd.to_datetime(frame[date_column]),
                "account_code": account,
                "source_table": (
                    "fact_dtc_order_line" if account == "4000" else "fact_wholesale_invoice_line"
                ),
                "source_id": frame[id_column].to_numpy(),
                "source_line": frame[line_column].to_numpy(),
                "product_key": frame["product_key"].to_numpy(),
                "amount": frame[amount_column].to_numpy(),
            }
        )
        frames.append(bridge)
    if not frames:
        return pd.DataFrame(
            columns=[
                "date",
                "account_code",
                "source_table",
                "source_id",
                "source_line",
                "product_key",
                "amount",
            ]
        )
    return pd.concat(frames, ignore_index=True)


def bus_matrix_frame() -> pd.DataFrame:
    """The bus matrix as a table, for the architecture doc and for the conformance test."""
    dimensions = sorted({d for dims in BUS_MATRIX.values() for d in dims})
    rows = []
    for fact, dims in BUS_MATRIX.items():
        row = {"fact": fact}
        row.update({d: ("x" if d in dims else "") for d in dimensions})
        rows.append(row)
    return pd.DataFrame(rows)
