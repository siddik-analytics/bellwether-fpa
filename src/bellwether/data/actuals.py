"""Transaction-level actuals for FY2023–FY2025 — contract §5.1, §5.2, §5.3.

Generation is shape-first, then scaled. Seasonality, concentration, promotional timing and
return lag all come from the simulated behaviour; a single scaling factor per year then pins
revenue to the contract target. Generating bottom-up and hoping to land on $10.6M would produce
either a wrong number or a fudge buried in a driver.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bellwether.data import config as C


def _daily_weights(
    dates: pd.DatetimeIndex, monthly: list[float], rng: np.random.Generator
) -> np.ndarray:
    """Within-month uniform, across-month per the contract seasonality, plus mild daily noise."""
    months = dates.month.to_numpy() - 1
    days_in_month = dates.days_in_month.to_numpy()
    w = np.asarray(monthly)[months] / days_in_month
    w = w * rng.uniform(0.82, 1.18, size=len(dates))
    return w / w.sum()


def generate_dtc(
    products: pd.DataFrame,
    spine: pd.DataFrame,
    rng: np.random.Generator,
    demand_gross_up: dict[int, float] | None = None,
    periods: list[tuple[int, C.YearDrivers]] | None = None,
    sku_mask: np.ndarray | None = None,
    first_order_id: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """DTC order lines and the customer dimension.

    Grain: one row per line of a DTC order, keyed ``(order_id, line_number)``.

    ``periods`` defaults to the actual years. The near-term forecast passes scenario-derived
    drivers for FY2026 instead, so it projects **this** demand model rather than running a
    second one — same seasonality, same SKU concentration, same basket shape, different
    drivers (contract §8, phase 3 D-d).

    ``sku_mask`` zeroes the selection probability for pruned SKUs, which is how the
    Consolidation scenario cuts the class-C tail without a separate code path.
    """
    order_frames, customer_rows = [], []
    next_customer = 1
    # Picking a SKU with probability proportional to revenue_weight / price makes realised
    # revenue share match the concentration weights rather than the unit share.
    sku_p = (products["revenue_weight"] / products["msrp"]).to_numpy()
    if sku_mask is not None:
        sku_p = sku_p * sku_mask
    sku_p = sku_p / sku_p.sum()
    sku_keys = products["product_key"].to_numpy()
    msrp = products["msrp"].to_numpy()
    ret_rate = products["return_rate"].to_numpy()
    next_order = first_order_id

    for year, d in periods or [(y, C.ACTUALS[y]) for y in C.ACTUAL_YEARS]:
        net_per_order = d.aov * (1 - C.DTC_RETURN_RATE) + C.DTC_SHIPPING_REVENUE_PER_ORDER
        # Demand is grossed up so revenue lands on target *after* stockout
        # suppression removes the lost share (§6.6).
        gross_up = (demand_gross_up or {}).get(year, 1.0)
        n_orders = round(d.revenue * d.dtc_share / net_per_order * gross_up)

        days = spine.loc[spine["year"] == year, "date"]
        dates = pd.DatetimeIndex(days.to_numpy())
        p = _daily_weights(dates, C.DTC_MONTHLY_SEASONALITY, rng)
        order_day_idx = rng.choice(len(dates), size=n_orders, p=p)
        order_dates = dates.to_numpy()[np.sort(order_day_idx)]

        n_lines = rng.choice([1, 2, 3], size=n_orders, p=[0.65, 0.28, 0.07])
        line_order_idx = np.repeat(np.arange(n_orders), n_lines)
        total_lines = len(line_order_idx)

        sku_idx = rng.choice(len(sku_p), size=total_lines, p=sku_p)
        qty = rng.choice([1, 2], size=total_lines, p=[0.80, 0.20])

        line_dates = order_dates[line_order_idx]
        promo_map = spine.set_index("date")["is_promotional"]
        on_promo = promo_map.reindex(pd.DatetimeIndex(line_dates)).to_numpy()
        # Revenue "generated during some form of promotional activity" is the contract's 27%
        # measure (§7.4), so every line on a promotional day counts. The 16% realised discount
        # is an average across them and already embeds the fact that promotions are targeted
        # rather than site-wide.
        promoted = on_promo.astype(bool)
        discount_rate = np.where(
            promoted, np.clip(rng.normal(C.PROMO_AVG_DISCOUNT, 0.035, total_lines), 0.05, 0.35), 0.0
        )

        gross = qty * msrp[sku_idx]
        discount = gross * discount_rate
        net = gross - discount

        # Scale so the realised net AOV matches the contract input for the year.
        realised_aov = net.sum() / n_orders
        scale = d.aov / realised_aov
        gross, discount, net = gross * scale, discount * scale, net * scale

        order_value = np.bincount(line_order_idx, weights=net, minlength=n_orders)
        # Free shipping over the threshold; below it most customers pay. Tuned to the 35% share.
        pays = np.where(
            order_value >= C.FREE_SHIPPING_THRESHOLD,
            rng.random(n_orders) < 0.12,
            rng.random(n_orders) < 0.62,
        )
        ship_rev_order = np.where(pays, C.DTC_SHIPPING_CHARGE, 0.0)
        ship_scale = C.DTC_SHIPPING_REVENUE_PER_ORDER / max(ship_rev_order.mean(), 1e-9)
        ship_rev_order = ship_rev_order * ship_scale
        # Allocate order-level shipping revenue across its lines by value share.
        line_share = np.where(
            order_value[line_order_idx] > 0,
            net / np.maximum(order_value[line_order_idx], 1e-9),
            0.0,
        )
        ship_rev_line = ship_rev_order[line_order_idx] * line_share

        # Customers: a share of orders are first-time, the rest repeat buyers.
        non_paid = C.NON_PAID_NEW_CUSTOMER_SHARE[year]
        new_share = 1.0 / (1.0 + C.REPEAT_RATE_12M * 2.2)
        is_first = rng.random(n_orders) < new_share
        n_new = int(is_first.sum())
        channels = [c[0] for c in C.ACQUISITION_CHANNELS]
        paid_flags = np.array([c[2] for c in C.ACQUISITION_CHANNELS])
        ch_p = np.array([c[1] for c in C.ACQUISITION_CHANNELS])
        ch_p = np.where(paid_flags, ch_p * (1 - non_paid), ch_p * non_paid)
        ch_p = ch_p / ch_p.sum()
        new_channel_idx = rng.choice(len(channels), size=n_new, p=ch_p)

        customer_key = np.empty(n_orders, dtype=np.int64)
        new_keys = np.arange(next_customer, next_customer + n_new)
        customer_key[is_first] = new_keys
        pool = np.arange(1, next_customer + n_new)
        customer_key[~is_first] = rng.choice(pool, size=n_orders - n_new)
        for k, ci in zip(new_keys, new_channel_idx, strict=True):
            customer_rows.append((int(k), channels[ci], bool(paid_flags[ci])))
        next_customer += n_new

        order_ids = np.arange(next_order, next_order + n_orders)
        next_order += n_orders

        frame = pd.DataFrame(
            {
                "order_id": order_ids[line_order_idx],
                "line_number": np.concatenate([np.arange(1, n + 1) for n in n_lines]),
                "order_date": line_dates,
                "customer_key": customer_key[line_order_idx],
                "product_key": sku_keys[sku_idx],
                "quantity": qty.astype("int16"),
                "gross_merchandise_value": gross,
                "promotional_discount": discount,
                "net_merchandise_value": net,
                "shipping_revenue_allocated": ship_rev_line,
                "is_promoted": promoted,
                "is_first_order": is_first[line_order_idx],
                "return_rate": ret_rate[sku_idx],
                "fiscal_year": year,
            }
        )
        order_frames.append(frame)

    lines = pd.concat(order_frames, ignore_index=True)
    customers = pd.DataFrame(
        customer_rows, columns=["customer_key", "acquisition_channel", "is_paid_acquired"]
    )
    first = lines.groupby("customer_key", as_index=False)["order_date"].min()
    customers = customers.merge(first, on="customer_key", how="left")
    customers = customers.rename(columns={"order_date": "first_order_date"})
    customers["first_order_cohort"] = (
        pd.to_datetime(customers["first_order_date"]).dt.to_period("M").astype(str)
    )
    counts = lines.groupby("customer_key")["order_id"].nunique()
    customers["lifetime_order_count"] = (
        customers["customer_key"].map(counts).fillna(0).astype("int32")
    )
    customers["geography"] = pd.Categorical(
        np.take(["Northeast", "Midwest", "South", "West"], rng.integers(0, 4, size=len(customers)))
    )
    return lines, customers


def generate_wholesale(
    products: pd.DataFrame,
    accounts: pd.DataFrame,
    spine: pd.DataFrame,
    rng: np.random.Generator,
    demand_gross_up: dict[int, float] | None = None,
    periods: list[tuple[int, C.YearDrivers]] | None = None,
    account_mask: np.ndarray | None = None,
    sku_mask: np.ndarray | None = None,
    first_invoice_id: int = 1,
) -> pd.DataFrame:
    """Wholesale invoice lines.

    Grain: one row per line of a wholesale invoice/shipment, keyed ``(invoice_id, line_number)``.
    """
    frames = []
    next_invoice = first_invoice_id
    sku_p = (products["revenue_weight"] / products["msrp"]).to_numpy()
    if sku_mask is not None:
        sku_p = sku_p * sku_mask
    sku_p = sku_p / sku_p.sum()

    # A pruned account places no orders at all, and its share is redistributed over the accounts
    # that remain — which is what pruning to the profitable tier actually does.
    if account_mask is not None:
        accounts = accounts.loc[account_mask.astype(bool)].copy()
        accounts["revenue_weight"] = accounts["revenue_weight"] / accounts["revenue_weight"].sum()
    sku_keys = products["product_key"].to_numpy()
    msrp = products["msrp"].to_numpy()

    for year, d in periods or [(y, C.ACTUALS[y]) for y in C.ACTUAL_YEARS]:
        ws_net_target = d.revenue * (1 - d.dtc_share) * (demand_gross_up or {}).get(year, 1.0)
        days = spine.loc[spine["year"] == year, "date"]
        dates = pd.DatetimeIndex(days.to_numpy())
        p = _daily_weights(dates, C.WS_MONTHLY_SEASONALITY, rng)

        rows = []
        for acc in accounts.itertuples():
            acc_net = ws_net_target * acc.revenue_weight
            n_orders = {"National": 12, "Regional": 8, "Independent": 5}[acc.tier]
            order_day_idx = rng.choice(len(dates), size=n_orders, p=p)
            for oi, day_idx in enumerate(np.sort(order_day_idx)):
                n_lines = int(rng.integers(8, 26))
                sku_idx = rng.choice(len(sku_p), size=n_lines, p=sku_p, replace=False)
                cartons = rng.integers(2, 14, size=n_lines)
                units = cartons * C.WS_CARTON_UNITS
                gross_unit = msrp[sku_idx] * (1 - acc.msrp_discount)
                gross = units * gross_unit
                rows.append(
                    pd.DataFrame(
                        {
                            "invoice_id": next_invoice + oi,
                            "line_number": np.arange(1, n_lines + 1),
                            "account_key": acc.account_key,
                            "shipment_date": dates[day_idx],
                            "product_key": sku_keys[sku_idx],
                            "cartons": cartons.astype("int16"),
                            "units": units.astype("int32"),
                            "gross_invoice_amount": gross,
                            "deduction_rate": acc.deduction_rate,
                            "payment_terms_days": acc.payment_terms_days,
                            "realised_dso": acc.realised_dso,
                            "account_share": acc_net,
                            "fiscal_year": year,
                        }
                    )
                )
            next_invoice += n_orders

        year_df = pd.concat(rows, ignore_index=True)
        # Scale per account so each lands on its concentration share, then the year lands on target.
        acc_gross = year_df.groupby("account_key")["gross_invoice_amount"].transform("sum")
        target_gross = (
            year_df["account_share"] / (1 - year_df["deduction_rate"]) / (1 - C.WS_RETURN_RATE)
        )
        factor = target_gross / acc_gross
        for col in ("gross_invoice_amount",):
            year_df[col] = year_df[col] * factor
        year_df["units"] = np.maximum(1, (year_df["units"] * factor).round()).astype("int32")
        frames.append(year_df.drop(columns=["account_share"]))

    lines = pd.concat(frames, ignore_index=True)
    lines["invoice_date"] = lines["shipment_date"]
    lines["co_op_allowance"] = lines["gross_invoice_amount"] * lines["deduction_rate"] * 0.45
    lines["markdown_allowance"] = lines["gross_invoice_amount"] * lines["deduction_rate"] * 0.30
    lines["chargeback"] = lines["gross_invoice_amount"] * lines["deduction_rate"] * 0.17
    lines["other_deduction"] = lines["gross_invoice_amount"] * lines["deduction_rate"] * 0.08
    deductions = (
        lines["co_op_allowance"]
        + lines["markdown_allowance"]
        + lines["chargeback"]
        + lines["other_deduction"]
    )
    lines["total_deductions"] = deductions
    lines["net_revenue"] = lines["gross_invoice_amount"] - deductions
    lines["due_date"] = lines["invoice_date"] + pd.to_timedelta(
        lines["payment_terms_days"], unit="D"
    )
    lines["collection_date"] = lines["invoice_date"] + pd.to_timedelta(
        lines["realised_dso"].astype(int), unit="D"
    )
    return lines


def generate_returns(dtc: pd.DataFrame, ws: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Returns, each linked to its originating sale line.

    Grain: one row per returned line. Preserves the originating sale period so return lag and
    reserve adequacy are testable — contract §5.3.
    """
    # DTC: sampled at the product-category rate, so category mix moves the blended rate.
    hit = rng.random(len(dtc)) < dtc["return_rate"].to_numpy()
    d = dtc.loc[hit].copy()
    lag = np.clip(rng.normal(C.DTC_RETURN_LAG_MEAN, C.DTC_RETURN_LAG_SD, len(d)), 2, 75)
    dtc_ret = pd.DataFrame(
        {
            "source": "DTC",
            "source_id": d["order_id"].to_numpy(),
            "source_line": d["line_number"].to_numpy(),
            "customer_key": d["customer_key"].to_numpy(),
            "account_key": 0,
            "product_key": d["product_key"].to_numpy(),
            "sale_date": d["order_date"].to_numpy(),
            "quantity": d["quantity"].to_numpy(),
            "refund_amount": d["net_merchandise_value"].to_numpy(),
            "lag_days": lag.round().astype(int),
            "recovery_rate": C.DTC_RETURN_RECOVERY,
        }
    )

    hit_ws = rng.random(len(ws)) < C.WS_RETURN_RATE
    w = ws.loc[hit_ws].copy()
    lag_w = rng.integers(C.WS_RETURN_LAG_MIN, C.WS_RETURN_LAG_MAX + 1, len(w))
    ws_ret = pd.DataFrame(
        {
            "source": "Wholesale",
            "source_id": w["invoice_id"].to_numpy(),
            "source_line": w["line_number"].to_numpy(),
            "customer_key": 0,
            "account_key": w["account_key"].to_numpy(),
            "product_key": w["product_key"].to_numpy(),
            "sale_date": w["shipment_date"].to_numpy(),
            "quantity": w["units"].to_numpy(),
            "refund_amount": w["net_revenue"].to_numpy(),
            "lag_days": lag_w,
            "recovery_rate": C.WS_RETURN_RECOVERY,
        }
    )

    ret = pd.concat([dtc_ret, ws_ret], ignore_index=True)
    ret["return_initiation_date"] = ret["sale_date"] + pd.to_timedelta(
        (ret["lag_days"] * 0.6).round().astype(int), unit="D"
    )
    ret["return_receipt_date"] = ret["sale_date"] + pd.to_timedelta(ret["lag_days"], unit="D")
    ret["refund_date"] = ret["return_receipt_date"] + pd.Timedelta(days=2)
    ret["recoverable_quantity"] = (ret["quantity"] * ret["recovery_rate"]).round().astype("int32")
    ret["non_sellable_quantity"] = ret["quantity"] - ret["recoverable_quantity"]
    ret["return_reason"] = pd.Categorical(
        np.take(
            ["Fit / size", "Not as expected", "Damaged in transit", "Defect", "Changed mind"],
            rng.integers(0, 5, size=len(ret)),
        )
    )
    ret.insert(0, "return_id", np.arange(1, len(ret) + 1, dtype="int64"))
    return ret
