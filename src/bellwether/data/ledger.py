"""Double-entry general ledger — contract §5.8.

Grain: one row per GL account x department x posting date x version x scenario.

Every journal balances by construction, which is what makes the trial balance sum to zero
without a plug. Debits are positive, credits negative; a journal that does not net to zero is a
bug, and ``post`` asserts it rather than letting it reach the fact table.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bellwether.data import config as C
from bellwether.data.inventory import LandedCost

CASH = "1000"
AR = "1100"
PROCESSOR = "1150"
INVENTORY = "1200"
INVENTORY_RESERVE = "1210"
RETURN_ASSET = "1250"
ADVANCES = "1300"
PPE = "1400"
AP = "2000"
REFUND_LIABILITY = "2200"
REVOLVER = "2500"
EQUITY = "3000"

CORP = "Executive / Corporate"
OPERATING_PLAN = "Balanced Base"


class Journal:
    """Accumulates balanced postings and flattens them to the ledger fact."""

    def __init__(self) -> None:
        self._rows: list[tuple] = []

    def post(self, date, legs: list[tuple[str, str, float]], memo: str) -> None:
        """Post one balanced journal. ``legs`` are (account_code, department, amount)."""
        total = sum(leg[2] for leg in legs)
        if abs(total) > 0.005:
            raise AssertionError(f"journal '{memo}' does not balance by {total:.4f}")
        for account, department, amount in legs:
            if amount:
                self._rows.append((date, account, department, float(amount), memo))

    def frame(self) -> pd.DataFrame:
        df = pd.DataFrame(
            self._rows, columns=["date", "account_code", "department_name", "amount", "memo"]
        )
        return df.groupby(["date", "account_code", "department_name", "memo"], as_index=False)[
            "amount"
        ].sum()


def _split_landed(value: float) -> list[float]:
    s = C.LANDED_COST_SPLIT
    return [value * s["product"], value * s["inbound_freight"], value * s["duty"]]


def build(
    dtc: pd.DataFrame,
    ws: pd.DataFrame,
    returns: pd.DataFrame,
    inv: pd.DataFrame,
    pos: pd.DataFrame,
    products: pd.DataFrame,
    spine: pd.DataFrame,
    landed: np.ndarray,
    dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Post every actual transaction. Returns the ledger fact at daily grain."""
    j = Journal()
    cost = LandedCost(products, dates)
    day = pd.Grouper(key="order_date", freq="D")

    # --- Opening balance sheet ---------------------------------------------------------
    # The simulation seeds day-one stock so the first quarter is not artificially starved. That
    # inventory is real and has to enter the ledger, funded by opening capital — without it the
    # control account sits below its subledger by the value of the seed, which is exactly the
    # kind of difference a subledger reconciliation exists to surface.
    opening = inv[inv["date"] == dates[0]]
    if not opening.empty:
        opening_value = float(
            cost.value(opening["date"], opening["product_key"], opening["opening_units"]).sum()
        )
        if opening_value:
            j.post(
                dates[0],
                [
                    (INVENTORY, "Supply Chain / Operations", opening_value),
                    (EQUITY, CORP, -opening_value),
                ],
                "Opening inventory",
            )

    # --- DTC revenue, daily -----------------------------------------------------------
    d = dtc.groupby(day)[
        [
            "gross_merchandise_value",
            "promotional_discount",
            "net_merchandise_value",
            "shipping_revenue_allocated",
        ]
    ].sum()
    for date, r in d.iterrows():
        cash_in = r["net_merchandise_value"] + r["shipping_revenue_allocated"]
        j.post(
            date,
            [
                (PROCESSOR, "Marketing / Ecommerce", cash_in),
                ("4100", "Marketing / Ecommerce", r["promotional_discount"]),
                ("4000", "Marketing / Ecommerce", -r["gross_merchandise_value"]),
                ("4020", "Marketing / Ecommerce", -r["shipping_revenue_allocated"]),
            ],
            "DTC sale",
        )

    # Processor settles three calendar days later (§6.12).
    for date, r in d.iterrows():
        settle = date + pd.Timedelta(days=C.PROCESSOR_SETTLEMENT_DAYS)
        if settle > dates[-1]:
            continue
        cash_in = r["net_merchandise_value"] + r["shipping_revenue_allocated"]
        j.post(
            settle,
            [(CASH, "Finance", cash_in), (PROCESSOR, "Marketing / Ecommerce", -cash_in)],
            "Processor settlement",
        )

    # DTC variable cost of delivery — parcel and pick-and-pack, per order (§6.3).
    orders = dtc.groupby(day)["order_id"].nunique()
    for date, n in orders.items():
        parcel, fulfil = n * C.DTC_PARCEL_COST, n * C.DTC_FULFILMENT_COST
        j.post(
            date,
            [
                ("5100", "Supply Chain / Operations", parcel),
                ("5200", "Supply Chain / Operations", fulfil),
                (CASH, "Finance", -(parcel + fulfil)),
            ],
            "DTC delivery cost",
        )

    # --- Wholesale revenue --------------------------------------------------------------
    wday = pd.Grouper(key="shipment_date", freq="D")
    w = ws.groupby(wday)[
        [
            "gross_invoice_amount",
            "co_op_allowance",
            "markdown_allowance",
            "chargeback",
            "other_deduction",
            "net_revenue",
        ]
    ].sum()
    for date, r in w.iterrows():
        j.post(
            date,
            [
                (AR, "Wholesale Sales", r["net_revenue"]),
                ("4130", "Wholesale Sales", r["co_op_allowance"]),
                ("4140", "Wholesale Sales", r["markdown_allowance"]),
                ("4150", "Wholesale Sales", r["chargeback"] + r["other_deduction"]),
                ("4010", "Wholesale Sales", -r["gross_invoice_amount"]),
            ],
            "Wholesale sale",
        )

    wc = ws.groupby(pd.Grouper(key="collection_date", freq="D"))["net_revenue"].sum()
    for date, amount in wc.items():
        if date > dates[-1]:
            continue
        j.post(
            date,
            [(CASH, "Finance", amount), (AR, "Wholesale Sales", -amount)],
            "Wholesale collection",
        )

    wu = ws.groupby(wday)["units"].sum()
    for date, units in wu.items():
        freight = ws.loc[ws["shipment_date"] == date, "net_revenue"].sum() * C.WS_FREIGHT_PCT_OF_NET
        fulfil = units * C.WS_FULFILMENT_PER_UNIT
        j.post(
            date,
            [
                ("5110", "Supply Chain / Operations", freight),
                ("5210", "Supply Chain / Operations", fulfil),
                (CASH, "Finance", -(freight + fulfil)),
            ],
            "Wholesale delivery cost",
        )

    # --- COGS released from inventory as units ship ------------------------------------
    ship_val = (inv["shipments"].to_numpy().reshape(len(dates), len(products)) * landed).sum(axis=1)
    for i, date in enumerate(dates):
        if ship_val[i] <= 0:
            continue
        prod, frt, duty = _split_landed(ship_val[i])
        j.post(
            date,
            [
                ("5000", "Supply Chain / Operations", prod),
                ("5010", "Supply Chain / Operations", frt),
                ("5020", "Supply Chain / Operations", duty),
                (INVENTORY, "Supply Chain / Operations", -ship_val[i]),
            ],
            "COGS on shipment",
        )

    # --- Returns: reserve at sale, unwound on receipt (ADR 0002) ------------------------
    r_dtc = returns[returns["source"] == "DTC"]
    r_ws = returns[returns["source"] == "Wholesale"]
    for frame, account, dept in (
        (r_dtc, "4110", "Marketing / Ecommerce"),
        (r_ws, "4120", "Wholesale Sales"),
    ):
        by_sale = frame.groupby(pd.Grouper(key="sale_date", freq="D"))["refund_amount"].sum()
        for date, amount in by_sale.items():
            j.post(
                date,
                [(account, dept, amount), (REFUND_LIABILITY, "Finance", -amount)],
                "Returns reserve",
            )

    returns = returns.copy()
    returns["_dtc_refund"] = returns["refund_amount"].where(returns["source"] == "DTC", 0.0)
    # Valued per SKU, then aggregated to the day. Valuing the day's aggregate at one rate is
    # what put the inventory control account $1.7M away from its subledger.
    in_window = pd.to_datetime(returns["return_receipt_date"]).isin(dates)
    returns.loc[in_window, "_rec_value"] = cost.value(
        returns.loc[in_window, "return_receipt_date"],
        returns.loc[in_window, "product_key"],
        returns.loc[in_window, "recoverable_quantity"],
    )
    returns.loc[in_window, "_scrap_value"] = cost.value(
        returns.loc[in_window, "return_receipt_date"],
        returns.loc[in_window, "product_key"],
        returns.loc[in_window, "non_sellable_quantity"],
    )
    returns[["_rec_value", "_scrap_value"]] = returns[["_rec_value", "_scrap_value"]].fillna(0.0)
    by_receipt = returns.groupby(pd.Grouper(key="return_receipt_date", freq="D")).agg(
        refund=("refund_amount", "sum"),
        dtc_refund=("_dtc_refund", "sum"),
        rec_value=("_rec_value", "sum"),
        scrap_value=("_scrap_value", "sum"),
    )
    for date, r in by_receipt.iterrows():
        if date > dates[-1]:
            continue
        # The reserve was booked to contra-revenue at the sale (4110/4120). Its settlement is a
        # balance-sheet movement and must not touch revenue again — hence the separate
        # utilisation accounts, without which "returns for March" is ambiguous between the
        # reserve booked on March sales and the reserve released against March receipts, and the
        # two differ by the return lag. See ADR 0017.
        dtc_share = r["dtc_refund"] / r["refund"] if r["refund"] else 0.0
        j.post(
            date,
            [
                ("4111", "Marketing / Ecommerce", r["refund"] * dtc_share),
                ("4121", "Wholesale Sales", r["refund"] * (1 - dtc_share)),
                (REFUND_LIABILITY, "Finance", r["refund"]),
                (CASH, "Finance", -r["refund"]),
                (REFUND_LIABILITY, "Finance", -r["refund"]),
            ],
            "Refund liability utilisation",
        )
        # Recovered units go back to stock and reverse the COGS booked when they shipped.
        # Non-recoverable units are already expensed through COGS on that shipment, so the only
        # entry they need is a reclassification into the return write-off account, which the
        # contract requires to be reported separately from shrink (§6.5).
        rec_val, scrap_val = r["rec_value"], r["scrap_value"]
        j.post(
            date,
            [
                (INVENTORY, "Supply Chain / Operations", rec_val),
                ("5000", "Supply Chain / Operations", -rec_val),
            ],
            "Return to stock",
        )
        j.post(
            date,
            [
                ("5320", "Supply Chain / Operations", scrap_val),
                ("5000", "Supply Chain / Operations", -scrap_val),
            ],
            "Return write-off reclass",
        )

    # --- Purchasing: deposit, receipt, balance payment (§5.6) ---------------------------
    if len(pos):
        pos = pos.copy()
        receipt = pd.to_datetime(pos["actual_receipt_date"]).clip(upper=dates[-1])
        pos["value"] = cost.value(receipt, pos["product_key"], pos["quantity"])
        for date, r in (
            pos.groupby(pd.Grouper(key="deposit_date", freq="D"))
            .apply(
                lambda g: pd.Series({"dep": (g["value"] * g["deposit_pct"]).sum()}),
                include_groups=False,
            )
            .iterrows()
        ):
            j.post(
                date,
                [(ADVANCES, "Supply Chain / Operations", r["dep"]), (CASH, "Finance", -r["dep"])],
                "Supplier deposit",
            )

        received = pos[pos.get("received_in_window", True)]
        recv = received.groupby(pd.Grouper(key="actual_receipt_date", freq="D")).apply(
            lambda g: pd.Series(
                {"val": g["value"].sum(), "dep": (g["value"] * g["deposit_pct"]).sum()}
            ),
            include_groups=False,
        )
        for date, r in recv.iterrows():
            if date > dates[-1]:
                continue
            j.post(
                date,
                [
                    (INVENTORY, "Supply Chain / Operations", r["val"]),
                    (ADVANCES, "Supply Chain / Operations", -r["dep"]),
                    (AP, "Finance", -(r["val"] - r["dep"])),
                ],
                "Inventory receipt",
            )

        bal = received.groupby(pd.Grouper(key="balance_due_date", freq="D")).apply(
            lambda g: pd.Series({"bal": (g["value"] * (1 - g["deposit_pct"])).sum()}),
            include_groups=False,
        )
        for date, r in bal.iterrows():
            if date > dates[-1] or date < dates[0]:
                continue
            j.post(
                date,
                [(AP, "Finance", r["bal"]), (CASH, "Finance", -r["bal"])],
                "Supplier balance payment",
            )

    # --- Operating expense, monthly -----------------------------------------------------
    months = pd.date_range(dates[0], dates[-1], freq="MS")
    dtc_rev_m = dtc.groupby(pd.Grouper(key="order_date", freq="MS"))[
        ["net_merchandise_value", "shipping_revenue_allocated"]
    ].sum()
    ws_rev_m = ws.groupby(pd.Grouper(key="shipment_date", freq="MS"))["net_revenue"].sum()
    inv_val = (inv["closing_units"].to_numpy().reshape(len(dates), len(products)) * landed).sum(
        axis=1
    )
    inv_series = pd.Series(inv_val, index=dates)

    for m in months:
        year = m.year
        d_year = C.ACTUALS.get(year)
        if d_year is None:
            continue
        month_dtc = dtc_rev_m.reindex([m]).fillna(0.0).iloc[0]
        month_ws = float(ws_rev_m.reindex([m]).fillna(0.0).iloc[0])
        revenue = float(month_dtc.sum()) + month_ws

        # The roster shape is FY2025's; each year's payroll is scaled to that year's headcount.
        # Dividing by the year's headcount instead of the roster total inflates every earlier
        # year by roster_total / headcount — 27% in FY2023.
        roster_total = sum(n for n, _ in C.ROSTER_2025.values())
        payroll = d_year.compensation * d_year.headcount / 12
        legs = [
            ("6000", dept, payroll * n / roster_total)
            for dept, (n, _) in C.ROSTER_2025.items()
            if n
        ]
        legs.append((CASH, "Finance", -sum(a for _, _, a in legs)))
        j.post(m, legs, "Payroll")

        marketing = revenue * d_year.marketing_pct
        perf = marketing * C.PERFORMANCE_SHARE_OF_MARKETING
        j.post(
            m,
            [
                ("6100", "Marketing / Ecommerce", perf),
                ("6110", "Marketing / Ecommerce", marketing - perf),
                (CASH, "Finance", -marketing),
            ],
            "Marketing",
        )

        proc = float(month_dtc.sum()) * C.PAYMENT_PROCESSING_PCT
        j.post(
            m,
            [("6200", "Marketing / Ecommerce", proc), (CASH, "Finance", -proc)],
            "Payment processing",
        )

        scale = d_year.fixed_costs / sum(C.FIXED_COST_LINES_2025.values())
        legs = [
            (code, C.FIXED_COST_DEPARTMENT[name], amount * scale / 12)
            for name, amount in C.FIXED_COST_LINES_2025.items()
            for code in [
                {
                    "3PL storage and account fees": "6300",
                    "Office and facilities": "6310",
                    "Software and technology": "6320",
                    "Professional fees": "6330",
                    "Insurance": "6340",
                    "Other corporate": "6350",
                }[name]
            ]
        ]
        legs.append((CASH, "Finance", -sum(a for _, _, a in legs)))
        j.post(m, legs, "Fixed operating costs")

        bad = month_ws * C.BAD_DEBT_PCT
        j.post(m, [("6400", "Finance", bad), ("1180", "Finance", -bad)], "Bad debt")

        month_mask = (dates >= m) & (dates < m + pd.offsets.MonthBegin(1))
        avg_inv = float(inv_series[month_mask].mean()) if month_mask.any() else 0.0
        shrink = avg_inv * d_year.shrink_pct / 12
        # Shrink is a valuation reserve, not a unit movement (§6.5) — inventory is written down
        # when net realisable value falls below cost, and no units leave the warehouse. Posting
        # it against the inventory control account instead put that account $45k below its
        # subledger, because the subledger has no corresponding movement to record.
        j.post(
            m,
            [
                ("5310", "Supply Chain / Operations", shrink),
                (INVENTORY_RESERVE, "Supply Chain / Operations", -shrink),
            ],
            "Shrink and damage",
        )

        dep = C.CAPEX_PER_YEAR / 12
        j.post(m, [("6500", CORP, dep), (PPE, CORP, -dep)], "Depreciation")

    # --- Equity raise (§6.10) -------------------------------------------------------------
    raise_date = pd.Timestamp(C.EQUITY_RAISE_DATE)
    if dates[0] <= raise_date <= dates[-1]:
        j.post(
            raise_date,
            [(CASH, "Finance", C.EQUITY_RAISE), (EQUITY, CORP, -C.EQUITY_RAISE)],
            "Equity raise",
        )

    ledger = j.frame()
    ledger["version_name"] = "Actual"
    # Actuals carry the operating plan scenario, not a "Not applicable" member — §3.3 defines
    # performance variance as a same-scenario comparison, and N/A would make every variance in
    # the model cross a dimension boundary the contract says to hold fixed. See ADR 0016.
    ledger["scenario_name"] = OPERATING_PLAN
    return ledger


def trial_balance(ledger: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    """Trial balance by period. Every period must net to zero (§9 check 5)."""
    df = ledger.copy()
    df["period"] = df["date"].dt.to_period("M").astype(str)
    return df.groupby("period", as_index=False)["amount"].sum()
