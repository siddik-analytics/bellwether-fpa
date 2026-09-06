"""Every calibration target from ``docs/data-contract.md`` §7, in one place.

No literal from the contract is written at a call site. When a contract figure changes, it
changes here and the validation suite catches whatever no longer ties.

The seed lives here rather than at a call site so that the whole dataset is reproducible from a
single value, which is what makes acceptance criteria testable at all.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

SEED = 20260905

SPINE_START = dt.date(2023, 1, 1)
SPINE_END = dt.date(2028, 12, 31)
ACTUAL_YEARS = (2023, 2024, 2025)
FORECAST_YEARS = (2026, 2027, 2028)


@dataclass(frozen=True)
class YearDrivers:
    """Bounded generator inputs for one fiscal year — contract §7.5 and §7.6."""

    revenue: float
    dtc_share: float
    aov: float
    landed_cost: float
    inventory_turns: float
    headcount: int
    compensation: float
    fixed_costs: float
    marketing_pct: float
    shrink_pct: float
    dso: float
    paid_cac: float


#: Contract §7.5. FY2025 is the anchor; FY2023-24 are bounded inputs derived from it.
ACTUALS: dict[int, YearDrivers] = {
    2023: YearDrivers(
        8_100_000, 0.7200, 74.50, 14.12, 2.8, 22, 98_500, 598_000, 0.1100, 0.010, 48, 27.0
    ),
    2024: YearDrivers(
        9_300_000, 0.6600, 76.25, 14.12, 2.6, 25, 102_400, 758_000, 0.1200, 0.010, 50, 29.0
    ),
    2025: YearDrivers(
        10_600_000, 0.5896, 78.00, 15.00, 2.4, 28, 106_464, 1_163_000, 0.1368, 0.025, 52, 34.0
    ),
}

#: Contract §7.6. Growth is applied to the prior year's revenue.
SCENARIOS: dict[str, dict[int, dict]] = {
    "Balanced Base": {
        2026: dict(
            growth=0.110,
            dtc_share=0.580,
            aov=79.60,
            landed_cost=15.15,
            inventory_turns=2.8,
            headcount=28,
            compensation=110_800,
            fixed_costs=1_210_000,
            marketing_pct=0.132,
            shrink_pct=0.018,
            dso=50,
            paid_cac=33.0,
        ),
        2027: dict(
            growth=0.100,
            dtc_share=0.575,
            aov=81.20,
            landed_cost=15.30,
            inventory_turns=2.9,
            headcount=29,
            compensation=115_200,
            fixed_costs=1_260_000,
            marketing_pct=0.126,
            shrink_pct=0.013,
            dso=50,
            paid_cac=32.0,
        ),
        2028: dict(
            growth=0.090,
            dtc_share=0.570,
            aov=82.80,
            landed_cost=15.45,
            inventory_turns=3.0,
            headcount=30,
            compensation=119_800,
            fixed_costs=1_300_000,
            marketing_pct=0.120,
            shrink_pct=0.010,
            dso=49,
            paid_cac=31.0,
        ),
    },
    "Wholesale Acceleration": {
        2026: dict(
            growth=0.170,
            dtc_share=0.530,
            aov=79.60,
            landed_cost=15.15,
            inventory_turns=2.6,
            headcount=29,
            compensation=110_800,
            fixed_costs=1_250_000,
            marketing_pct=0.118,
            shrink_pct=0.020,
            dso=53,
            paid_cac=34.0,
        ),
        2027: dict(
            growth=0.160,
            dtc_share=0.485,
            aov=81.20,
            landed_cost=15.30,
            inventory_turns=2.65,
            headcount=32,
            compensation=115_200,
            fixed_costs=1_340_000,
            marketing_pct=0.108,
            shrink_pct=0.019,
            dso=56,
            paid_cac=34.0,
        ),
        2028: dict(
            growth=0.140,
            dtc_share=0.450,
            aov=82.80,
            landed_cost=15.45,
            inventory_turns=2.7,
            headcount=34,
            compensation=119_800,
            fixed_costs=1_430_000,
            marketing_pct=0.102,
            shrink_pct=0.018,
            dso=58,
            paid_cac=33.0,
        ),
    },
    "DTC Recovery / Margin": {
        2026: dict(
            growth=0.070,
            dtc_share=0.610,
            aov=80.40,
            landed_cost=15.15,
            inventory_turns=2.9,
            headcount=28,
            compensation=110_800,
            fixed_costs=1_190_000,
            marketing_pct=0.134,
            shrink_pct=0.015,
            dso=49,
            paid_cac=32.0,
        ),
        2027: dict(
            growth=0.070,
            dtc_share=0.630,
            aov=82.80,
            landed_cost=15.30,
            inventory_turns=3.1,
            headcount=28,
            compensation=115_200,
            fixed_costs=1_220_000,
            marketing_pct=0.129,
            shrink_pct=0.011,
            dso=48,
            paid_cac=30.0,
        ),
        2028: dict(
            growth=0.080,
            dtc_share=0.650,
            aov=85.20,
            landed_cost=15.45,
            inventory_turns=3.2,
            headcount=29,
            compensation=119_800,
            fixed_costs=1_250_000,
            marketing_pct=0.124,
            shrink_pct=0.010,
            dso=47,
            paid_cac=29.0,
        ),
    },
}

# --- unit economics, contract §7.1 --------------------------------------------------------

UNITS_PER_ORDER = 1.70
DTC_PARCEL_COST = 7.25
DTC_FULFILMENT_COST = 3.25
DTC_SHIPPING_REVENUE_PER_ORDER = 2.43
DTC_SHIPPING_PAID_SHARE = 0.35
DTC_SHIPPING_CHARGE = 6.95
FREE_SHIPPING_THRESHOLD = 75.00

WS_FREIGHT_PCT_OF_NET = 0.018
WS_FULFILMENT_PER_UNIT = 0.45
WS_CARTON_UNITS = 12
WS_NET_PRICE_PER_UNIT = 25.10
WS_DEDUCTION_PCT = 0.030
WS_MSRP_DISCOUNT = 0.46

PAYMENT_PROCESSING_PCT = 0.029
BAD_DEBT_PCT = 0.004

# --- returns, §6.1 and §5.3 ---------------------------------------------------------------

DTC_RETURN_RATE = 0.070
DTC_RETURN_RECOVERY = 0.80
DTC_RETURN_LAG_MEAN = 18
DTC_RETURN_LAG_SD = 7
WS_RETURN_RATE = 0.015
WS_RETURN_RECOVERY = 0.50
WS_RETURN_LAG_MIN = 45
WS_RETURN_LAG_MAX = 90

#: Return rate by product category — §4.1. Category mix moves the blended rate on its own.
RETURN_RATE_BY_CATEGORY = {
    "Drinkware": 0.055,
    "Food storage": 0.075,
    "Seasonal": 0.095,
    "Accessories": 0.035,
}

# --- promotional calendar, §7.4 -----------------------------------------------------------

PROMO_REVENUE_SHARE = 0.27
PROMO_AVG_DISCOUNT = 0.16
#: (start month, start day, end month, end day, label)
PROMO_WINDOWS = [
    (3, 15, 4, 10, "Spring"),
    (6, 10, 6, 24, "Summer"),
    (8, 20, 9, 12, "Back to school"),
    (11, 22, 12, 1, "Black Friday / Cyber Monday"),
    (12, 10, 12, 21, "Holiday gifting"),
]

DTC_MONTHLY_SEASONALITY = [
    0.065,
    0.060,
    0.075,
    0.075,
    0.070,
    0.080,
    0.065,
    0.080,
    0.080,
    0.080,
    0.150,
    0.120,
]
WS_MONTHLY_SEASONALITY = [
    0.070,
    0.090,
    0.090,
    0.080,
    0.070,
    0.070,
    0.080,
    0.100,
    0.110,
    0.100,
    0.080,
    0.060,
]

# --- inventory and purchasing, §5.4 and §5.5 ----------------------------------------------

SAFETY_STOCK_WEEKS = {"A": 5.5, "B": 3.5, "C": 1.0}
REPLENISHMENT_LEAD_DAYS = 90
LAUNCH_LEAD_DAYS = 135
MOQ_BY_FAMILY = {"Drinkware": 1_200, "Food storage": 1_000, "Accessories": 750, "Seasonal": 2_000}
PO_CANCELLATION_DAYS_BEFORE_RECEIPT = 55

#: Class C is bought as finite seasonal runs rather than continuously replenished (§4.1).
#: June buy lands for autumn/holiday; November buy lands for spring.
SEASONAL_BUY_MONTHS = (6, 11)
SEASONAL_RUN_DAYS = 180

#: Solved inventory operating point — see ADR 0011. These are the settings at which the
#: generator meets the 4% hero-SKU service target; the turns that result are the relaxed
#: contract targets, not the other way round.
INVENTORY_CLASS_A_SAFETY_MULTIPLIER = 1.25
#: FY2025 onward is 2.4x the FY2023-24 base. That multiple is the inventory over-commitment the
#: story requires: purchases placed before demand softened, plus the February launch overhang.
INVENTORY_WOS_SCALE = {2023: 0.30, 2024: 0.30, 2025: 0.72, 2026: 0.72, 2027: 0.72, 2028: 0.72}

LANDED_COST_SPLIT = {"product": 0.78, "inbound_freight": 0.12, "duty": 0.10}

INVENTORY_AGE_BUCKETS = [(0, 180, 0.00), (181, 270, 0.10), (271, 365, 0.25), (366, 10_000, 0.60)]

# --- events, §1.3 -------------------------------------------------------------------------

SUPPLIER_COST_INCREASE_DATE = dt.date(2025, 4, 1)
SUPPLIER_COST_INCREASE_PCT = 0.08
LAUNCH_DATE = dt.date(2025, 2, 1)
LAUNCH_SHORTFALL_VS_PLAN = 0.35
STOCKOUT_DEMAND_SHARE = 0.04
STOCKOUT_LOST_SHARE = 0.50

# --- financing, §6.10 ---------------------------------------------------------------------

FACILITY = 2_000_000.0
AR_ADVANCE_RATE = 0.85
INVENTORY_ADVANCE_RATE = 0.50
INVENTORY_SUBLIMIT = 1_000_000.0
AR_ELIGIBLE_SHARE = 0.92
INVENTORY_ELIGIBLE_SHARE = 0.88
DILUTION_RESERVE = 0.02
CONCENTRATION_CAP = 0.25
MIN_EXCESS_AVAILABILITY = 250_000.0
MIN_CASH_POLICY = 500_000.0
SOFR = 0.040
SPREAD = 0.035
UNUSED_LINE_FEE = 0.005
EQUITY_RAISE = 3_500_000.0
EQUITY_RAISE_DATE = dt.date(2024, 6, 15)
OPENING_CASH = 400_000.0
CAPEX_PER_YEAR = 50_000.0

# --- product catalogue, §4.1 --------------------------------------------------------------

SKU_COUNT = 85
FAMILY_COUNTS = {"Drinkware": 35, "Food storage": 25, "Accessories": 15, "Seasonal": 10}
#: Revenue share by rank band — top 5 ≈ 38%, top 10 ≈ 55%, class A/B/C ≈ 55/30/15.
CONCENTRATION_BANDS = [(5, 0.38), (10, 0.55), (35, 0.85), (85, 1.00)]
CLASS_BOUNDARIES = {"A": (0, 10), "B": (10, 35), "C": (35, 85)}

# --- wholesale accounts, §4.3 -------------------------------------------------------------

WS_ACCOUNT_COUNT = 38
#: Share of wholesale revenue for the ranked accounts; the remainder is spread over the tail.
WS_TOP_ACCOUNT_SHARES = [0.24, 0.15, 0.10, 0.07, 0.06]
WS_TIERS = {
    "National": dict(discount=0.49, terms=60, deduction=0.052, dso_offset=11, count=5),
    "Regional": dict(discount=0.45, terms=45, deduction=0.028, dso_offset=3, count=11),
    "Independent": dict(discount=0.40, terms=30, deduction=0.012, dso_offset=7, count=22),
}

# --- departments and people, §4.4 and §5.9 -------------------------------------------------

DEPARTMENTS = [
    "Executive / Corporate",
    "Finance",
    "People / Administration",
    "Supply Chain / Operations",
    "Product / Merchandising",
    "Marketing / Ecommerce",
    "Wholesale Sales",
    "Customer Experience",
    "Technology / Shared Services",
]

#: FY2025 roster — contract §5.9. Headcount and cost by cost centre.
ROSTER_2025 = {
    "Executive / Corporate": (2, 395_000),
    "People / Administration": (1, 80_000),
    "Finance": (3, 350_000),
    "Supply Chain / Operations": (4, 420_000),
    "Product / Merchandising": (5, 480_000),
    "Marketing / Ecommerce": (7, 701_000),
    "Wholesale Sales": (3, 365_000),
    "Customer Experience": (3, 190_000),
    "Technology / Shared Services": (0, 0),
}

#: Fixed cost base composition — §7.2.
FIXED_COST_LINES_2025 = {
    "3PL storage and account fees": 228_000,
    "Office and facilities": 150_000,
    "Software and technology": 280_000,
    "Professional fees": 210_000,
    "Insurance": 95_000,
    "Other corporate": 200_000,
}

FIXED_COST_DEPARTMENT = {
    "3PL storage and account fees": "Supply Chain / Operations",
    "Office and facilities": "People / Administration",
    "Software and technology": "Technology / Shared Services",
    "Professional fees": "Finance",
    "Insurance": "Finance",
    "Other corporate": "Executive / Corporate",
}

# --- marketing, §6.8 and §6.9 --------------------------------------------------------------

PERFORMANCE_SHARE_OF_MARKETING = 0.68
NON_PAID_NEW_CUSTOMER_SHARE = {
    2023: 0.38,
    2024: 0.34,
    2025: 0.30,
    2026: 0.30,
    2027: 0.31,
    2028: 0.32,
}
REPEAT_RATE_12M = 0.29
ACQUISITION_CHANNELS = [
    ("Paid social", 0.38, True),
    ("Paid search", 0.15, True),
    ("Affiliate / creator", 0.08, True),
    ("Retargeting", 0.07, True),
    ("Email / SMS", 0.07, False),
    ("Organic", 0.15, False),
    ("Referral", 0.10, False),
]

# --- settlement, §6.12 ----------------------------------------------------------------------

PROCESSOR_SETTLEMENT_DAYS = 3
SUPPLIER_TERMS = {
    "strategic": dict(deposit=0.20, balance_days_after_shipment=30),
    "core": dict(deposit=0.30, balance_days_after_shipment=30),
    "launch": dict(deposit=0.50, balance_days_after_shipment=-5),
}

SAMPLE_ROWS = 1_000


@dataclass(frozen=True)
class Config:
    """Runtime configuration. Everything is defaulted from the contract."""

    seed: int = SEED
    spine_start: dt.date = SPINE_START
    spine_end: dt.date = SPINE_END
    actual_years: tuple[int, ...] = ACTUAL_YEARS
    forecast_years: tuple[int, ...] = FORECAST_YEARS
    sample_rows: int = SAMPLE_ROWS
    actuals: dict[int, YearDrivers] = field(default_factory=lambda: dict(ACTUALS))

    def landed_cost_on(self, day: dt.date) -> float:
        """Landed cost is effective-dated — ADR 0003. The April 2025 step is product cost only."""
        year = min(max(day.year, 2023), 2028)
        if year in self.actuals:
            return self.actuals[year].landed_cost
        return SCENARIOS["Balanced Base"][year]["landed_cost"]
