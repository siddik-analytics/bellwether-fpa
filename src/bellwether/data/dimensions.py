"""Conformed dimensions — contract §4.

Grain: one row per member, except the Type 2 dimensions, which carry one row per version of a
member with a closed-open ``[valid_from, valid_to)`` effective range.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from bellwether.data import config as C


def build_date_spine() -> pd.DataFrame:
    """Grain: one row per calendar day from 2023-01-01 to 2028-12-31, contiguous."""
    days = pd.date_range(C.SPINE_START, C.SPINE_END, freq="D")
    df = pd.DataFrame({"date": days})
    df["date_key"] = df["date"].dt.strftime("%Y%m%d").astype("int32")
    df["year"] = df["date"].dt.year.astype("int16")
    df["month"] = df["date"].dt.month.astype("int8")
    df["day"] = df["date"].dt.day.astype("int8")
    df["quarter"] = df["date"].dt.quarter.astype("int8")
    df["month_start"] = df["date"].values.astype("datetime64[M]").astype("datetime64[ns]")
    df["day_of_week"] = df["date"].dt.dayofweek.astype("int8")
    df["is_banking_day"] = (df["day_of_week"] < 5).astype(bool)
    df["is_actual"] = df["year"].isin(C.ACTUAL_YEARS)

    promo = np.full(len(df), "", dtype=object)
    for m0, d0, m1, d1, label in C.PROMO_WINDOWS:
        for year in range(C.SPINE_START.year, C.SPINE_END.year + 1):
            start = pd.Timestamp(year, m0, d0)
            end = pd.Timestamp(year, m1, d1)
            promo[(df["date"] >= start) & (df["date"] <= end)] = label
    df["promotion"] = promo
    df["is_promotional"] = df["promotion"] != ""
    return df


def _concentration_weights() -> np.ndarray:
    """Revenue weights by SKU rank satisfying the §4.1 concentration constraints.

    A two-parameter power law ``w_i ∝ (i + c) ** -b``, solved for the constraints rather than
    hand-tuned. Per-band geometric decay was tried first and rejected: it is monotone *within*
    each band but jumps upward at band boundaries, so the ten largest SKUs by weight are not the
    first ten ranks and the top-10 share overshoots.
    """
    ranks = np.arange(1, C.SKU_COUNT + 1)
    targets = [(0, 5, 0.38), (0, 10, 0.55), (10, 35, 0.30), (35, C.SKU_COUNT, 0.15)]

    def error(b: float, c: float) -> float:
        w = (ranks + c) ** -b
        w /= w.sum()
        return sum((w[lo:hi].sum() - target) ** 2 for lo, hi, target in targets)

    b_lo, b_hi, c_lo, c_hi = 0.6, 3.5, 0.05, 6.0
    best_b, best_c = 1.6, 5.4
    for _ in range(3):  # coarse grid, then two refinements around the incumbent
        grid = [
            (error(b, c), b, c)
            for b in np.linspace(b_lo, b_hi, 40)
            for c in np.linspace(c_lo, c_hi, 40)
        ]
        _, best_b, best_c = min(grid)
        b_span, c_span = (b_hi - b_lo) / 8, (c_hi - c_lo) / 8
        b_lo, b_hi = best_b - b_span, best_b + b_span
        c_lo, c_hi = max(0.01, best_c - c_span), best_c + c_span

    weights = (ranks + best_c) ** -best_b
    return weights / weights.sum()


def build_products(rng: np.random.Generator) -> pd.DataFrame:
    """Grain: one row per SKU version. Type 2 on class, lifecycle and category."""
    weights = _concentration_weights()

    # Hero SKUs are drinkware; the long tail skews to accessories and seasonal.
    families: list[str] = []
    order = ["Drinkware", "Food storage", "Accessories", "Seasonal"]
    remaining = dict(C.FAMILY_COUNTS)
    for rank in range(C.SKU_COUNT):
        if rank < 12:
            pool = ["Drinkware", "Food storage"]
        elif rank < 40:
            pool = ["Drinkware", "Food storage", "Accessories"]
        else:
            pool = ["Accessories", "Seasonal", "Food storage", "Drinkware"]
        pool = [f for f in pool if remaining[f] > 0] or [f for f in order if remaining[f] > 0]
        pick = pool[rank % len(pool)]
        families.append(pick)
        remaining[pick] -= 1

    rows = []
    for rank in range(C.SKU_COUNT):
        family = families[rank]
        sku_class = next(k for k, (lo, hi) in C.CLASS_BOUNDARIES.items() if lo <= rank < hi)
        category = "Seasonal" if family == "Seasonal" else family
        base_msrp = {
            "Drinkware": 46.0,
            "Food storage": 38.0,
            "Accessories": 17.0,
            "Seasonal": 52.0,
        }[family]
        msrp = round(base_msrp * float(rng.uniform(0.80, 1.28)), 2)
        cost_index = {
            "Drinkware": 1.00,
            "Food storage": 0.92,
            "Accessories": 0.42,
            "Seasonal": 1.10,
        }[family]
        rows.append(
            dict(
                sku_code=f"NL-{family[:2].upper()}-{rank + 1:03d}",
                product_family=family,
                category=category,
                sku_class=sku_class,
                is_hero=rank < 5,
                revenue_weight=weights[rank],
                msrp=msrp,
                cost_index=cost_index * float(rng.uniform(0.94, 1.06)),
                case_pack_units=C.WS_CARTON_UNITS,
                moq=C.MOQ_BY_FAMILY[family],
                return_rate=C.RETURN_RATE_BY_CATEGORY[category],
                lifecycle_state="core" if sku_class in ("A", "B") else "seasonal",
                launch_date=pd.Timestamp(C.SPINE_START),
            )
        )

    df = pd.DataFrame(rows)

    # The February 2025 insulated food-storage launch — §1.3. Six SKUs, launched together,
    # deliberately too broad an assortment for the demand that materialised.
    launch_idx = df.index[(df["product_family"] == "Food storage") & (df["sku_class"] == "C")][:6]
    df.loc[launch_idx, "lifecycle_state"] = "launch"
    df.loc[launch_idx, "launch_date"] = pd.Timestamp(C.LAUNCH_DATE)
    df.loc[launch_idx, "moq"] = 1_500

    # Normalise landed cost so the unit-weighted portfolio average matches the contract anchor.
    df["cost_index"] = df["cost_index"] / (df["cost_index"] * df["revenue_weight"]).sum()

    # Category return rates vary (§4.1) but their revenue-weighted mean is the headline 7% (§5.3).
    # Without this both cannot hold, and the mix-weighted rate lands near 5.9% instead.
    weighted = (df["return_rate"] * df["revenue_weight"]).sum()
    df["return_rate"] = df["return_rate"] * C.DTC_RETURN_RATE / weighted
    df.insert(0, "product_key", np.arange(1, len(df) + 1, dtype="int32"))
    df["valid_from"] = pd.Timestamp(C.SPINE_START)
    df["valid_to"] = pd.Timestamp(C.SPINE_END) + pd.Timedelta(days=1)
    return df


def build_wholesale_accounts(rng: np.random.Generator) -> pd.DataFrame:
    """Grain: one row per account version. Type 2 on tier, terms and freight terms."""
    shares = list(C.WS_TOP_ACCOUNT_SHARES)
    tail_n = C.WS_ACCOUNT_COUNT - len(shares)
    tail_total = 1.0 - sum(shares)
    decay = np.power(0.94, np.arange(tail_n))
    shares += list(tail_total * decay / decay.sum())

    tiers: list[str] = []
    for tier, spec in C.WS_TIERS.items():
        tiers += [tier] * spec["count"]
    tiers = tiers[: C.WS_ACCOUNT_COUNT]

    rows = []
    for i, (share, tier) in enumerate(zip(shares, tiers, strict=True)):
        spec = C.WS_TIERS[tier]
        rows.append(
            dict(
                account_code=f"WS-{i + 1:03d}",
                account_name=f"Account {i + 1:03d}",
                tier=tier,
                revenue_weight=share,
                msrp_discount=spec["discount"],
                payment_terms_days=spec["terms"],
                deduction_rate=spec["deduction"] * float(rng.uniform(0.85, 1.15)),
                realised_dso=spec["terms"] - 6 + spec["dso_offset"],
                northlake_paid_freight=bool(rng.random() < (0.20 if tier == "National" else 0.55)),
                credit_quality="Low risk"
                if tier == "National"
                else ("Medium" if tier == "Regional" else "Watch"),
                is_individually_forecast=i < 5,
            )
        )
    df = pd.DataFrame(rows)
    df.insert(0, "account_key", np.arange(1, len(df) + 1, dtype="int32"))
    df["valid_from"] = pd.Timestamp(C.SPINE_START)
    df["valid_to"] = pd.Timestamp(C.SPINE_END) + pd.Timedelta(days=1)
    return df


def build_suppliers() -> pd.DataFrame:
    """Grain: one row per supplier version. Type 2 on payment-term structure."""
    rows = [
        dict(
            supplier_code="SUP-001",
            supplier_name="Primary drinkware manufacturer",
            term_type="core",
            country="Asia",
        ),
        dict(
            supplier_code="SUP-002",
            supplier_name="Secondary drinkware manufacturer",
            term_type="strategic",
            country="Asia",
        ),
        dict(
            supplier_code="SUP-003",
            supplier_name="Food storage manufacturer",
            term_type="core",
            country="Asia",
        ),
        dict(
            supplier_code="SUP-004",
            supplier_name="Accessories manufacturer",
            term_type="core",
            country="Asia",
        ),
        dict(
            supplier_code="SUP-005",
            supplier_name="Seasonal / limited edition",
            term_type="launch",
            country="Asia",
        ),
    ]
    df = pd.DataFrame(rows)
    for col, key in (("deposit_pct", "deposit"), ("balance_days", "balance_days_after_shipment")):
        df[col] = df["term_type"].map(lambda t, k=key: C.SUPPLIER_TERMS[t][k])
    df.insert(0, "supplier_key", np.arange(1, len(df) + 1, dtype="int32"))
    df["valid_from"] = pd.Timestamp(C.SPINE_START)
    df["valid_to"] = pd.Timestamp(C.SPINE_END) + pd.Timedelta(days=1)
    return df


def build_departments() -> pd.DataFrame:
    """Grain: one row per cost centre."""
    df = pd.DataFrame({"department_name": C.DEPARTMENTS})
    df.insert(0, "department_key", np.arange(1, len(df) + 1, dtype="int32"))
    df["is_corporate"] = df["department_name"].isin(
        [
            "Executive / Corporate",
            "Finance",
            "People / Administration",
            "Technology / Shared Services",
        ]
    )
    return df


#: (code, name, statement, type, cost behaviour). Contract §5.8.
GL_ACCOUNTS: list[tuple[str, str, str, str, str]] = [
    ("1000", "Cash", "BS", "asset", "n/a"),
    ("1100", "Accounts receivable - wholesale", "BS", "asset", "n/a"),
    ("1150", "Payment processor receivable", "BS", "asset", "n/a"),
    ("1180", "Allowance for doubtful accounts", "BS", "contra_asset", "n/a"),
    ("1200", "Inventory - finished goods", "BS", "asset", "n/a"),
    ("1250", "Right of return asset", "BS", "asset", "n/a"),
    ("1300", "Supplier advances / prepaid inventory", "BS", "asset", "n/a"),
    ("1400", "Property and equipment, net", "BS", "asset", "n/a"),
    ("2000", "Accounts payable", "BS", "liability", "n/a"),
    ("2100", "Accrued liabilities", "BS", "liability", "n/a"),
    ("2200", "Refund liability", "BS", "liability", "n/a"),
    ("2500", "Revolving credit facility", "BS", "liability", "n/a"),
    ("3000", "Common stock and paid-in capital", "BS", "equity", "n/a"),
    ("3900", "Retained earnings", "BS", "equity", "n/a"),
    ("4000", "DTC merchandise revenue", "PL", "revenue", "variable"),
    ("4010", "Wholesale merchandise revenue", "PL", "revenue", "variable"),
    ("4020", "DTC shipping revenue", "PL", "revenue", "variable"),
    ("4100", "Promotional discounts", "PL", "contra_revenue", "variable"),
    ("4110", "DTC returns reserve", "PL", "contra_revenue", "variable"),
    ("4111", "DTC refund liability utilisation", "BS", "liability_movement", "n/a"),
    ("4120", "Wholesale returns reserve", "PL", "contra_revenue", "variable"),
    ("4121", "Wholesale refund liability utilisation", "BS", "liability_movement", "n/a"),
    ("4130", "Co-op marketing deductions", "PL", "contra_revenue", "variable"),
    ("4140", "Markdown allowances", "PL", "contra_revenue", "variable"),
    ("4150", "Chargebacks and compliance deductions", "PL", "contra_revenue", "variable"),
    ("5000", "COGS - product cost", "PL", "cogs", "variable"),
    ("5010", "COGS - inbound freight", "PL", "cogs", "variable"),
    ("5020", "COGS - duty and customs", "PL", "cogs", "variable"),
    ("5100", "COGS - outbound parcel freight", "PL", "cogs", "variable"),
    ("5110", "COGS - wholesale outbound freight", "PL", "cogs", "variable"),
    ("5200", "COGS - DTC pick and pack", "PL", "cogs", "variable"),
    ("5210", "COGS - wholesale fulfilment", "PL", "cogs", "variable"),
    ("5220", "COGS - packaging", "PL", "cogs", "variable"),
    ("5300", "COGS - inventory write-downs", "PL", "cogs", "variable"),
    ("5310", "COGS - shrink and damage", "PL", "cogs", "variable"),
    ("5320", "COGS - return write-offs", "PL", "cogs", "variable"),
    ("6000", "Payroll and benefits", "PL", "opex", "step_fixed"),
    ("6100", "Performance marketing", "PL", "opex", "variable"),
    ("6110", "Brand and retention marketing", "PL", "opex", "directly_budgeted"),
    ("6200", "Payment processing fees", "PL", "opex", "variable"),
    ("6300", "3PL storage and account fees", "PL", "opex", "step_fixed"),
    ("6310", "Office and facilities", "PL", "opex", "fixed"),
    ("6320", "Software and technology", "PL", "opex", "step_fixed"),
    ("6330", "Professional fees", "PL", "opex", "directly_budgeted"),
    ("6340", "Insurance", "PL", "opex", "fixed"),
    ("6350", "Other corporate", "PL", "opex", "directly_budgeted"),
    ("6400", "Bad debt expense", "PL", "opex", "variable"),
    ("6500", "Depreciation", "PL", "opex", "fixed"),
    ("7000", "Interest expense", "PL", "other", "variable"),
    ("7010", "Unused line fees", "PL", "other", "fixed"),
]


def build_gl_accounts() -> pd.DataFrame:
    """Grain: one row per general ledger account."""
    df = pd.DataFrame(
        GL_ACCOUNTS,
        columns=["account_code", "account_name", "statement", "account_type", "cost_behaviour"],
    )
    df.insert(0, "account_key", np.arange(1, len(df) + 1, dtype="int32"))
    df["is_pl"] = df["statement"] == "PL"
    return df


def build_versions() -> pd.DataFrame:
    """Grain: one row per version — contract §3.1."""
    return pd.DataFrame(
        {
            "version_key": np.arange(1, 5, dtype="int32"),
            "version_name": ["Actual", "Budget", "Prior Forecast", "Latest Forecast"],
            "is_frozen": [False, True, True, False],
        }
    )


def build_scenarios() -> pd.DataFrame:
    """Grain: one row per scenario — contract §3.2."""
    names = [
        "Balanced Base",
        "Wholesale Acceleration",
        "Consolidation / Path to Breakeven",
        "DTC Recovery / Margin",
    ]
    return pd.DataFrame(
        {
            "scenario_key": np.arange(1, len(names) + 1, dtype="int32"),
            "scenario_name": names,
            "is_operating_plan": [True, False, False, False],
        }
    )


def build_channels() -> pd.DataFrame:
    """Grain: one row per sales channel, plus the corporate member.

    Channel is the most-used slicer in the model — §6.7 contribution, §7.1 unit economics, three
    of four scenarios — and until now it was implicit in *which fact table you were reading*.
    That works in Python and fails in a BI tool, where one slicer must filter revenue, COGS,
    marketing and contribution together across facts.
    """
    return pd.DataFrame(
        {
            "channel_key": np.array([1, 2, 3], dtype="int32"),
            "channel_name": ["DTC", "Wholesale", "Unallocated corporate"],
            "is_revenue_channel": [True, True, False],
        }
    )


def build_locations() -> pd.DataFrame:
    """Grain: one row per stock location. In-transit is a location, not a flag."""
    return pd.DataFrame(
        {
            "location_key": np.array([1, 2], dtype="int32"),
            "location_name": ["3PL warehouse", "In transit"],
            "is_sellable": [True, False],
        }
    )


def build_employees(rng: np.random.Generator) -> pd.DataFrame:
    """Grain: one row per employee version. Type 2 on department, role and compensation."""
    rows, emp = [], 0
    hires_by_year = {2023: 22, 2024: 25, 2025: 28}
    per_dept = {d: n for d, (n, _) in C.ROSTER_2025.items()}
    cost_per_dept = {d: c for d, (_, c) in C.ROSTER_2025.items()}

    for dept, count in per_dept.items():
        if count == 0:
            continue
        avg = cost_per_dept[dept] / count
        for i in range(count):
            emp += 1
            # Earlier hires fill the FY2023 roster; later ones step in as thresholds are crossed.
            if i < max(1, int(count * 0.78)):
                start = dt.date(2022, 1, 1)
            elif emp % 2 == 0:
                start = dt.date(2024, int(rng.integers(2, 11)), 1)
            else:
                start = dt.date(2025, int(rng.integers(2, 11)), 1)
            rows.append(
                dict(
                    employee_code=f"EMP-{emp:03d}",
                    department_name=dept,
                    role=f"{dept.split(' /')[0]} role {i + 1}",
                    hire_date=pd.Timestamp(start),
                    departure_date=pd.NaT,
                    annual_salary=round(avg / 1.22, -2),
                    payroll_burden=round(avg - avg / 1.22, -2),
                    fully_loaded_cost=round(avg, -2),
                    bonus_eligible=i == 0,
                    planned_hire=False,
                )
            )
    df = pd.DataFrame(rows)
    df.insert(0, "employee_key", np.arange(1, len(df) + 1, dtype="int32"))
    df["valid_from"] = df["hire_date"]
    df["valid_to"] = pd.Timestamp(C.SPINE_END) + pd.Timedelta(days=1)
    assert len(df) == hires_by_year[2025], f"roster is {len(df)} FTE, expected 28"
    return df


def build_campaigns(rng: np.random.Generator) -> pd.DataFrame:
    """Grain: one row per marketing campaign."""
    rows = []
    for name, share, is_paid in C.ACQUISITION_CHANNELS:
        rows.append(
            dict(
                channel=name,
                spend_share=share,
                is_paid=is_paid,
                classification="Acquisition" if is_paid or name == "Referral" else "Retention",
            )
        )
    df = pd.DataFrame(rows)
    df.insert(0, "campaign_key", np.arange(1, len(df) + 1, dtype="int32"))
    return df


def build_promotions() -> pd.DataFrame:
    """Grain: one row per promotional event occurrence."""
    rows = []
    for year in range(C.SPINE_START.year, C.SPINE_END.year + 1):
        for m0, d0, m1, d1, label in C.PROMO_WINDOWS:
            rows.append(
                dict(
                    promotion_name=label,
                    year=year,
                    start_date=pd.Timestamp(year, m0, d0),
                    end_date=pd.Timestamp(year, m1, d1),
                    is_sitewide=label.startswith("Black Friday"),
                )
            )
    df = pd.DataFrame(rows)
    df.insert(0, "promotion_key", np.arange(1, len(df) + 1, dtype="int32"))
    return df


def build_all(rng: np.random.Generator) -> dict[str, pd.DataFrame]:
    return {
        "dim_date": build_date_spine(),
        "dim_product": build_products(rng),
        "dim_wholesale_account": build_wholesale_accounts(rng),
        "dim_supplier": build_suppliers(),
        "dim_department": build_departments(),
        "dim_gl_account": build_gl_accounts(),
        "dim_version": build_versions(),
        "dim_scenario": build_scenarios(),
        "dim_location": build_locations(),
        "dim_channel": build_channels(),
        "dim_employee": build_employees(rng),
        "dim_campaign": build_campaigns(rng),
        "dim_promotion": build_promotions(),
    }
