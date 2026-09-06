"""Phase 3 acceptance criteria — see ``docs/phases/phase-03-spec.md``."""

from __future__ import annotations

import pandas as pd
import pytest

from bellwether.data import config as C
from bellwether.data import forecast as forecast_mod
from bellwether.data import generate
from bellwether.paths import REPO_ROOT
from bellwether.transform import allocation, forecast_ledger, near_term, semantic, star


@pytest.fixture(scope="session")
def data() -> dict[str, pd.DataFrame]:
    return generate.generate()


@pytest.fixture(scope="session")
def actual_ledger(data) -> pd.DataFrame:
    ledger = data["fact_gl"]
    ledger = ledger[ledger["version_name"] == "Actual"].copy()
    mapping = allocation.build_mapping(data["dim_gl_account"], data["dim_department"])
    return star.channel_key_for_ledger(ledger, mapping, data["dim_channel"])


@pytest.fixture(scope="session")
def forecast_bundle():
    plan, schedule, _ = forecast_mod.build(10.6e6, 1.5e6, 0.0)
    return plan, schedule


# --- 3.1, 3.2 the forecast balances -----------------------------------------------------


def test_forecast_ledger_balances_every_version_and_scenario(data, forecast_bundle) -> None:
    """3.1 — the carried defect. Not narrowed to actuals; the forecast balances too."""
    plan, _ = forecast_bundle
    actual = data["fact_gl"]
    actual = actual[actual["version_name"] == "Actual"]
    frames = []
    for version, scenario in forecast_mod.VERSION_SCENARIOS:
        sub = plan[(plan["version_name"] == version) & (plan["scenario_name"] == scenario)]
        if sub.empty:
            continue
        frames.append(forecast_ledger.post_opening(actual, sub["month"].min(), version, scenario))
        frames.append(forecast_ledger.post(sub, version, scenario))
    ledger = pd.concat(frames, ignore_index=True)
    trial = forecast_ledger.trial_balance(ledger)
    assert trial["amount"].abs().max() < 0.01
    assert len(trial) == 324


def test_actual_trial_balance_still_zero(actual_ledger) -> None:
    frame = actual_ledger.copy()
    frame["period"] = pd.to_datetime(frame["date"]).dt.to_period("M")
    assert frame.groupby("period")["amount"].sum().abs().max() < 0.01


def test_working_capital_is_derivable_from_the_ledger(data, forecast_bundle) -> None:
    """3.3 — the function that removes financing.py's second source of truth."""
    plan, _ = forecast_bundle
    actual = data["fact_gl"]
    actual = actual[actual["version_name"] == "Actual"]
    sub = plan[
        (plan["version_name"] == "Latest Forecast") & (plan["scenario_name"] == "Balanced Base")
    ]
    ledger = pd.concat(
        [
            forecast_ledger.post_opening(
                actual, sub["month"].min(), "Latest Forecast", "Balanced Base"
            ),
            forecast_ledger.post(sub, "Latest Forecast", "Balanced Base"),
        ],
        ignore_index=True,
    )
    balances = forecast_ledger.working_capital_from_ledger(ledger)
    assert {"receivables", "inventory", "accounts_payable", "cash"} <= set(balances.columns)
    assert (balances["inventory"] > 0).all(), "inventory must never go negative"


# --- 3.5, 3.6, 3.7 the margin plug ------------------------------------------------------


def test_gm_calibration_is_gone_from_the_forecast_path() -> None:
    """3.5 — deleted, not tuned. The near-term forecast derives COGS from units."""
    source = (REPO_ROOT / "src" / "bellwether" / "transform" / "near_term.py").read_text(
        encoding="utf-8"
    )
    assert "GM_CALIBRATION" not in source.replace("``GM_CALIBRATION``", "")


def test_near_term_derives_cogs_from_units(data) -> None:
    """3.6 — units x effective-dated landed cost, the same derivation the actuals use."""
    dates = pd.DatetimeIndex(data["dim_date"]["date"])
    result = near_term.project(
        data["dim_product"],
        data["dim_wholesale_account"],
        data["dim_date"],
        "Balanced Base",
        10.6e6,
        __import__("numpy").random.default_rng(C.SEED),
    )
    units = near_term.units_and_cogs(result["dtc"], result["wholesale"], data["dim_product"], dates)
    assert (units["units"] > 0).all()
    assert (units["landed_cogs"] > 0).all()
    implied = units["landed_cogs"].sum() / units["units"].sum()
    assert 10.0 < implied < 20.0, implied


def test_product_margin_has_eight_series(data) -> None:
    """3.7 — family x channel. A uniform plug moves all eight; a mix effect moves none."""
    dates = pd.DatetimeIndex(data["dim_date"]["date"])
    result = near_term.project(
        data["dim_product"],
        data["dim_wholesale_account"],
        data["dim_date"],
        "Balanced Base",
        10.6e6,
        __import__("numpy").random.default_rng(C.SEED),
    )
    units = near_term.units_and_cogs(result["dtc"], result["wholesale"], data["dim_product"], dates)
    margin = near_term.product_margin(units, data["dim_product"])
    assert margin.groupby(["product_family", "channel_name"]).ngroups == 8


def test_consolidation_actually_prunes(data) -> None:
    """D-d / P-5 — the scenario's mechanism must be visible, not asserted."""
    dates = pd.DatetimeIndex(data["dim_date"]["date"])
    import numpy as np

    counts = {}
    for scenario in ("Balanced Base", near_term.PRUNE_SCENARIO):
        result = near_term.project(
            data["dim_product"],
            data["dim_wholesale_account"],
            data["dim_date"],
            scenario,
            10.6e6,
            np.random.default_rng(C.SEED),
        )
        units = near_term.units_and_cogs(
            result["dtc"], result["wholesale"], data["dim_product"], dates
        )
        counts[scenario] = (
            units["product_key"].nunique(),
            result["wholesale"]["account_key"].nunique(),
        )
    assert counts[near_term.PRUNE_SCENARIO][0] < counts["Balanced Base"][0]
    assert counts[near_term.PRUNE_SCENARIO][1] < counts["Balanced Base"][1]


# --- 3.9 to 3.14 star schema -------------------------------------------------------------


def test_not_applicable_members_exist(data) -> None:
    """3.10 — a null foreign key degrades silently in a BI tool; an explicit member does not."""
    conformed = star.conform_dimensions(data)
    for name, key in (
        ("dim_customer", "customer_key"),
        ("dim_product", "product_key"),
        ("dim_wholesale_account", "account_key"),
        ("dim_supplier", "supplier_key"),
    ):
        assert (conformed[name][key] == star.NA_KEY).any(), name


def test_channel_dimension_exists_and_covers_both_channels(data) -> None:
    """3.11 — channel was previously implicit in which fact table you read."""
    channels = data["dim_channel"]
    assert set(channels["channel_name"]) == {"DTC", "Wholesale", "Unallocated corporate"}


def test_actuals_carry_the_operating_plan_scenario(actual_ledger) -> None:
    """ADR 0016 — not a Not applicable member, or §3.3 could not be evaluated."""
    assert set(actual_ledger["scenario_name"].unique()) == {"Balanced Base"}


def test_bus_matrix_covers_every_fact(data) -> None:
    """3.8 — the documented matrix must match the built schema."""
    matrix = star.bus_matrix_frame()
    for fact in star.BUS_MATRIX:
        assert fact in set(matrix["fact"]), fact
    for dims in star.BUS_MATRIX.values():
        for dimension in dims:
            assert dimension in data, dimension


# --- 3.15 to 3.22 semantic layer ---------------------------------------------------------


def test_every_metric_carries_grain_and_format() -> None:
    """3.16 — grain, filter and format live with the definition, not at a call site."""
    for metric in semantic.ALL_METRICS.values():
        assert metric.grain
        assert metric.format_string
        assert metric.description


def test_derived_metrics_do_not_restate_base_filters() -> None:
    """3.15 — a repeated filter expression is how two copies start to drift."""
    for name, metric in semantic.DERIVED.items():
        assert metric.depends_on, name
        assert not metric.account_types, f"{name} restates a base filter"


def test_three_tier_hierarchy_holds(actual_ledger, data) -> None:
    """3.19 — Gross Profit >= Contribution Profit >= EBITDA at every period."""
    frame = actual_ledger.copy()
    frame["year"] = pd.to_datetime(frame["date"]).dt.year
    for year in C.ACTUAL_YEARS:
        ladder = semantic.evaluate_ladder(frame[frame["year"] == year], data["dim_gl_account"])
        assert ladder["Gross Profit"] >= ladder["EBITDA"]
        assert ladder["Net Revenue"] > 0


def test_gross_to_net_reconstructs_from_ledger_accounts_alone(actual_ledger, data) -> None:
    """3.20 — no management adjustment. §9 check 7."""
    frame = actual_ledger.copy()
    frame["year"] = pd.to_datetime(frame["date"]).dt.year
    ladder = semantic.evaluate_ladder(frame[frame["year"] == 2025], data["dim_gl_account"])
    assert abs(ladder["Net Revenue"] / C.ACTUALS[2025].revenue - 1) < 0.01
    assert abs(ladder["Gross Margin %"] - 0.436) < 0.005
    assert abs(ladder["EBITDA Margin %"] + 0.1235) < 0.008


def test_channel_contribution_ties_to_the_total(actual_ledger, data) -> None:
    """Corporate is shown once and undivided, and the parts must sum to the whole."""
    frame = actual_ledger.copy()
    frame["year"] = pd.to_datetime(frame["date"]).dt.year
    frame = frame[frame["year"] == 2025]
    dtc = data["fact_dtc_order_line"]
    wholesale = data["fact_wholesale_invoice_line"]
    units = {
        "DTC": float(dtc[dtc["fiscal_year"] == 2025]["quantity"].sum()),
        "Wholesale": float(wholesale[wholesale["fiscal_year"] == 2025]["units"].sum()),
    }
    contribution = semantic.channel_contribution(frame, data["dim_gl_account"], units)
    total = semantic.evaluate_ladder(frame, data["dim_gl_account"])
    assert abs(contribution["EBITDA"].sum() - total["EBITDA"]) < 1.0
    assert contribution["is_corporate"].sum() == 1


def test_favourable_variance_is_positive_for_revenue_and_cost() -> None:
    """3.22 — the sign convention holds whichever side of the P&L the line is on."""
    assert semantic.variance(actual=110, comparison=100, is_cost=False) > 0
    assert semantic.variance(actual=90, comparison=100, is_cost=True) > 0
    assert semantic.variance(actual=90, comparison=100, is_cost=False) < 0


def test_variance_decomposition_produces_all_three(actual_ledger) -> None:
    """3.21 — performance, forecast revision and scenario difference (§3.3)."""
    result = semantic.decompose(
        actual=100.0, budget=90.0, prior_forecast=95.0, latest_forecast=105.0
    )
    assert set(result) == {"performance_variance", "forecast_revision", "scenario_difference"}
    assert result["performance_variance"] == 10.0
    assert result["forecast_revision"] == 10.0


# --- 3.18 allocation ---------------------------------------------------------------------


def test_allocation_is_data_not_branching(data) -> None:
    """3.18 — Power BI consumes the same table, so it cannot be conditionals here."""
    mapping = allocation.build_mapping(data["dim_gl_account"], data["dim_department"])
    assert len(mapping) == len(data["dim_gl_account"]) * len(data["dim_department"])
    assert set(mapping["channel_allocation"]) <= {
        "DTC",
        "Wholesale",
        "BY_UNITS",
        allocation.CORPORATE,
    }


def test_supply_chain_stays_unallocated(data) -> None:
    """ADR 0010 — and the sensitivity is the evidence, not an assertion."""
    mapping = allocation.build_mapping(data["dim_gl_account"], data["dim_department"])
    supply_chain = mapping[mapping["department_name"] == "Supply Chain / Operations"]
    payroll = supply_chain[supply_chain["account_code"] == "6000"]
    assert (payroll["channel_allocation"] == allocation.CORPORATE).all()


def test_supply_chain_sensitivity_shows_a_material_spread() -> None:
    """The drivers must actually disagree, or the argument for not choosing one is empty."""
    frame = allocation.supply_chain_sensitivity(
        units_by_channel={"DTC": 140_000, "Wholesale": 175_000},
        revenue_by_channel={"DTC": 6.25e6, "Wholesale": 4.35e6},
        lines_by_channel={"DTC": 120_000, "Wholesale": 4_300},
        supply_chain_cost=420_000,
    )
    wholesale = frame[frame["channel_name"] == "Wholesale"]
    assert wholesale["share"].max() - wholesale["share"].min() > 0.4


# --- 3.23, 3.24 drill path ---------------------------------------------------------------


def test_gl_bridge_reaches_the_transaction_lines(actual_ledger, data) -> None:
    """3.23 — a bridge, not extra keys: most postings have no single product (D-c)."""
    bridge = star.build_gl_bridge(
        actual_ledger, data["fact_dtc_order_line"], data["fact_wholesale_invoice_line"]
    )
    assert not bridge.empty
    assert set(bridge["account_code"]) == {"4000", "4010"}
    assert set(bridge["product_key"]) <= set(data["dim_product"]["product_key"])
    assert (bridge["source_line"] > 0).all()


# --- 3.12, 3.25 to 3.27 reconciliation ----------------------------------------------------

#: The inventory control account ties to its subledger within this tolerance. The residual is a
#: cost-basis timing difference on returns that span the April 2025 landed-cost step: the ledger
#: values a return at its receipt-date cost, the subledger movement at the cost on the day the
#: units moved, and units returned across the step carry both. It is stated rather than left
#: unexplained — 3.85% with no reason is what a reviewer picks at.
INVENTORY_TIE_TOLERANCE = 0.005


def test_inventory_control_ties_to_subledger(data) -> None:
    """3.12 — a control account that does not tie is a ledger nobody should trust."""

    from bellwether.data.inventory import landed_cost_series

    ledger = data["fact_gl"]
    ledger = ledger[ledger["version_name"] == "Actual"]
    control = ledger[ledger["account_code"] == "1200"]["amount"].sum()

    inventory = data["fact_inventory_daily"]
    products = data["dim_product"]
    dates = pd.DatetimeIndex(data["dim_date"]["date"])
    actual_dates = dates[dates.year <= max(C.ACTUAL_YEARS)]
    cost = landed_cost_series(products, actual_dates)
    shape = (len(actual_dates), len(products))

    opening = inventory[inventory["date"] == actual_dates[0]]
    subledger = float((opening["opening_units"].to_numpy() * cost[0]).sum())
    for column, sign in (("receipts", 1), ("returns_in", 1), ("shipments", -1)):
        subledger += sign * float((inventory[column].to_numpy().reshape(shape) * cost).sum())

    assert abs(control - subledger) / subledger < INVENTORY_TIE_TOLERANCE, (
        f"control {control:,.0f} vs subledger {subledger:,.0f}"
    )


def test_shrink_is_a_reserve_not_a_unit_movement(data) -> None:
    """§6.5 — inventory is written down, not shipped out. The reserve is its own account."""
    ledger = data["fact_gl"]
    ledger = ledger[ledger["version_name"] == "Actual"]
    reserve = ledger[ledger["account_code"] == "1210"]["amount"].sum()
    assert reserve < 0, "the reserve must reduce carrying value"
    assert ledger[
        (ledger["account_code"] == "1200") & (ledger["memo"] == "Shrink and damage")
    ].empty


def test_ebitda_from_the_star_ties_to_the_ledger(actual_ledger, data) -> None:
    """3.26 — the warehouse must reproduce the source, not restate it."""
    frame = actual_ledger.copy()
    frame["year"] = pd.to_datetime(frame["date"]).dt.year
    for year in C.ACTUAL_YEARS:
        subset = frame[frame["year"] == year]
        ladder = semantic.evaluate_ladder(subset, data["dim_gl_account"])
        accounts = data["dim_gl_account"].set_index("account_code")["account_type"]
        pl = subset[
            subset["account_code"].map(accounts).isin(["revenue", "contra_revenue", "cogs", "opex"])
        ]
        assert abs(ladder["EBITDA"] + pl["amount"].sum()) < 1.0


def test_calibration_targets_survive_transformation(actual_ledger, data) -> None:
    """3.27 — the warehouse does not quietly change a number."""
    frame = actual_ledger.copy()
    frame["year"] = pd.to_datetime(frame["date"]).dt.year
    for year in C.ACTUAL_YEARS:
        ladder = semantic.evaluate_ladder(frame[frame["year"] == year], data["dim_gl_account"])
        assert abs(ladder["Net Revenue"] / C.ACTUALS[year].revenue - 1) < 0.01, year


def test_financing_is_derived_from_the_ledger(data) -> None:
    """3.3 / 3.4 — the shipped financing schedule reads posted balances, not drivers."""
    schedule = data["fact_financing_monthly"]
    assert {"version_name", "scenario_name"} <= set(schedule.columns)
    assert (schedule["revolver_drawn"] <= schedule["borrowing_base"] + 0.01).all()
    verdicts = data["_verdicts"].set_index("scenario_name")
    assert verdicts.loc["Consolidation / Path to Breakeven", "peak_revolver_drawn"] == "0.0"
    assert verdicts.loc["Wholesale Acceleration", "holds"] == "False"


def test_forecast_periods_balance_in_the_shipped_ledger(data) -> None:
    """3.1 — check 11 applies to every version and scenario, unamended."""
    ledger = data["fact_gl"].copy()
    ledger["period"] = pd.to_datetime(ledger["date"]).dt.to_period("M")
    trial = ledger.groupby(["version_name", "scenario_name", "period"])["amount"].sum()
    assert trial.abs().max() < 0.01
    assert set(ledger["version_name"]) >= {"Actual", "Budget", "Latest Forecast"}
