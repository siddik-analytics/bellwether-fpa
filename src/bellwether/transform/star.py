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

from bellwether.transform import allocation, semantic

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


#: Cost of goods both channels consume, split by the units each shipped. Materialised here
#: rather than applied downstream — ADR 0020. A consumer that had to re-implement this would be
#: a second definition of the §6.7 mapping, which is the failure ADR 0010 exists to prevent.
SPLIT_MARKER = "BY_UNITS"


def units_by_channel_month(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Units shipped per channel per month — the basis the §6.7 split is measured on.

    Measured, not chosen: DTC order quantities and wholesale shipped units, from the transaction
    facts themselves. Those facts cover actual periods only, so the forecast has no measured
    basis and the split cannot be made there — see ``materialise_channel_split``.
    """
    frames = []
    for name, date_column, unit_column, channel in (
        ("fact_dtc_order_line", "order_date", "quantity", "DTC"),
        ("fact_wholesale_invoice_line", "shipment_date", "units", "Wholesale"),
    ):
        frame = tables.get(name)
        if frame is None or frame.empty:
            continue
        piece = pd.DataFrame(
            {
                "month": pd.to_datetime(frame[date_column]).dt.to_period("M").dt.to_timestamp(),
                "units": frame[unit_column].astype("float64"),
                "channel_name": channel,
            }
        )
        frames.append(piece)
    if not frames:
        return pd.DataFrame(columns=["month", "channel_name", "units"])
    out = pd.concat(frames, ignore_index=True)
    return out.groupby(["month", "channel_name"], as_index=False)["units"].sum()


def materialise_channel_split(
    ledger: pd.DataFrame, channels: pd.DataFrame, units: pd.DataFrame
) -> pd.DataFrame:
    """Split shared cost of goods into channel rows, in the star — ADR 0020, §6.7.

    Every row the mapping sends to ``BY_UNITS`` becomes one row per channel, pro-rated by the
    units that channel shipped in that month. Totals are preserved exactly: the split
    redistributes an amount, it never changes one.

    Rows in a month with **no measured units** keep the corporate member and are flagged
    ``split_basis = "none"``. That is every forecast period, because units are measured from
    transaction facts and the forecast has none. Leaving them unallocated is the honest answer;
    inventing a forecast basis would be choosing an allocation while §6.7 says the split is
    measured.
    """
    lookup = channels.set_index("channel_name")["channel_key"].to_dict()
    out = ledger.copy()
    out["month"] = pd.to_datetime(out["date"]).dt.to_period("M").dt.to_timestamp()
    out["split_basis"] = "direct"

    shared = out[out["channel_allocation"] == SPLIT_MARKER]
    if shared.empty:
        return out.drop(columns=["month"])

    weights = units.pivot_table(
        index="month", columns="channel_name", values="units", aggfunc="sum"
    ).fillna(0.0)
    weights = weights.div(weights.sum(axis=1).replace(0.0, pd.NA), axis=0)

    pieces = []
    for channel in weights.columns:
        share = shared["month"].map(weights[channel])
        piece = shared.copy()
        piece["amount"] = piece["amount"] * share.fillna(0.0)
        piece["channel_allocation"] = channel
        piece["channel_key"] = lookup[channel]
        piece["split_basis"] = "units shipped"
        pieces.append(piece)

    # A month with no measured units keeps the whole amount on corporate rather than losing it.
    # BY_UNITS is an internal marker in the mapping, not a channel; it must not survive into the
    # star, where a consumer would render it as a third channel beside DTC and wholesale.
    corporate = "Unallocated corporate"
    unmeasured = shared[~shared["month"].isin(weights.dropna(how="all").index)].copy()
    unmeasured["channel_allocation"] = corporate
    unmeasured["channel_key"] = lookup[corporate]
    unmeasured["split_basis"] = "none"
    pieces.append(unmeasured)

    rebuilt = pd.concat(
        [out[out["channel_allocation"] != SPLIT_MARKER], *pieces], ignore_index=True
    )
    return rebuilt[rebuilt["amount"] != 0.0].drop(columns=["month"])


def build_star(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """The dimensional model consumers read — dollars, allocations resolved.

    This is the boundary ADR 0020 draws. Everything upstream is the generator's business;
    everything downstream reads this and nothing else, so anything a consumer would otherwise
    have to compute for itself is computed here.
    """
    conformed = conform_dimensions(tables)
    mapping = allocation.build_mapping(tables["dim_gl_account"], tables["dim_department"])
    ledger = channel_key_for_ledger(tables["fact_gl"], mapping, conformed["dim_channel"])
    units = units_by_channel_month(tables)
    ledger = materialise_channel_split(ledger, conformed["dim_channel"], units)

    star = dict(conformed)
    star["fact_gl"] = ledger
    star["bridge_channel_allocation"] = mapping
    star["dim_metric"] = semantic.definitions_frame()
    star["fact_metric"] = metric_facts(ledger, tables["dim_gl_account"])
    return star


def metric_facts(ledger: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    """Base metric values by month, version, scenario and channel — the BI fact table.

    Only **base** metrics are materialised. Derived metrics are not rows here because they are
    generated as measures from their own derivations (ADR 0019), and a Net Revenue row alongside
    a Net Revenue measure would be two answers to one question.

    Channel is part of the grain, so channel contribution in any consumer is a group-by over a
    fact whose allocation was already resolved (ADR 0020) rather than a calculation the consumer
    performs.
    """
    frame = ledger.copy()
    frame["month"] = pd.to_datetime(frame["date"]).dt.to_period("M").dt.to_timestamp()
    types = accounts.set_index("account_code")["account_type"]
    frame["account_type"] = frame["account_code"].map(types)

    keys = ["month", "version_name", "scenario_name", "channel_allocation"]
    pieces = []
    for name, metric in semantic.BASE.items():
        subset = frame[frame["account_type"].isin(metric.account_types)]
        if subset.empty:
            continue
        grouped = subset.groupby(keys, as_index=False)["amount"].sum()
        grouped["value"] = grouped["amount"] * metric.sign
        grouped["metric_name"] = name
        pieces.append(grouped[[*keys, "metric_name", "value"]])

    if not pieces:
        return pd.DataFrame(columns=[*keys, "metric_name", "value"])
    return pd.concat(pieces, ignore_index=True)
