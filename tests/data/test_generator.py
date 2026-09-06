"""Phase 2 acceptance criteria — see ``docs/phases/phase-02-spec.md``.

The dataset is generated once per session and shared, because generating it is the expensive
part and every assertion here reads the same output.
"""

from __future__ import annotations

import subprocess
import sys

import pandas as pd
import pytest

from bellwether.data import config as C
from bellwether.data import financing, generate
from bellwether.paths import REPO_ROOT

FACT_GRAINS = {
    "fact_dtc_order_line": ["order_id", "line_number"],
    "fact_wholesale_invoice_line": ["invoice_id", "line_number"],
    "fact_return_line": ["return_id"],
    "fact_inventory_daily": ["date", "product_key", "location_key"],
    "fact_purchase_order_line": ["po_id", "line_number"],
}

PII_FIELDS = {
    "name",
    "first_name",
    "last_name",
    "email",
    "phone",
    "address",
    "street",
    "postcode",
    "zip",
    "ssn",
    "dob",
}


@pytest.fixture(scope="session")
def data() -> dict[str, pd.DataFrame]:
    return generate.generate()


# --- 2.1, 2.2 determinism ---------------------------------------------------------------


def test_same_seed_produces_identical_output() -> None:
    """2.1 — determinism is what makes every other criterion testable."""
    first, second = generate.generate(seed=4242), generate.generate(seed=4242)
    for name in ("fact_dtc_order_line", "fact_gl", "fact_inventory_daily"):
        pd.testing.assert_frame_equal(first[name], second[name])


def test_different_seed_produces_different_output() -> None:
    """A generator that ignores its seed would pass 2.1 trivially."""
    a = generate.generate(seed=1)["fact_dtc_order_line"]
    b = generate.generate(seed=2)["fact_dtc_order_line"]
    assert not a["net_merchandise_value"].equals(b["net_merchandise_value"])


def test_no_wall_clock_or_unseeded_randomness() -> None:
    """2.2 — a single `datetime.now()` makes the dataset irreproducible."""
    for path in (REPO_ROOT / "src" / "bellwether" / "data").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "datetime.now" not in source, path.name
        assert "np.random.seed" not in source, path.name
        assert "random.random(" not in source, path.name


# --- 2.3, 2.4 build ----------------------------------------------------------------------


def test_headless_build_generates_the_dataset() -> None:
    """2.3 — the documented command produces the data with no Excel present."""
    result = subprocess.run(
        [sys.executable, "-m", "bellwether.build"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "generate synthetic source data" in result.stdout


def test_csv_samples_are_committed_and_current(data) -> None:
    """D-2 — the samples are a committed artifact, not generated output.

    `data/` is gitignored wholesale, so samples written under it were never committed and the
    browsing reviewer they exist for saw nothing. They live at the repo root instead.
    """
    samples = REPO_ROOT / "samples"
    assert samples.is_dir()
    assert (samples / "README.md").is_file()
    written = {p.stem for p in samples.glob("*.csv")}
    expected = {name for name in data if not name.startswith("_")}
    assert expected <= written, expected - written
    for path in samples.glob("*.csv"):
        assert path.stat().st_size < 512_000, f"{path.name} exceeds the pre-commit size limit"


def test_samples_are_not_gitignored() -> None:
    """The defect this replaced was invisible: the files existed and were never committed."""
    result = subprocess.run(
        ["git", "check-ignore", "samples/dim_product.csv"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    assert result.returncode != 0, "samples/ is gitignored; it must be committed"


# --- 2.6, 2.7, 2.8 structure --------------------------------------------------------------


@pytest.mark.parametrize(("table", "keys"), FACT_GRAINS.items())
def test_fact_is_unique_at_its_declared_grain(data, table: str, keys: list[str]) -> None:
    """2.6 — the grain in the module docstring is the grain in the data."""
    frame = data[table]
    if frame.empty:
        pytest.skip(f"{table} is empty")
    assert not frame.duplicated(subset=keys).any()


def test_no_orphan_keys(data) -> None:
    """2.7 — referential integrity across every fact-to-dimension join."""
    products = set(data["dim_product"]["product_key"])
    accounts = set(data["dim_wholesale_account"]["account_key"])
    assert set(data["fact_dtc_order_line"]["product_key"]) <= products
    assert set(data["fact_wholesale_invoice_line"]["product_key"]) <= products
    assert set(data["fact_wholesale_invoice_line"]["account_key"]) <= accounts
    assert set(data["fact_inventory_daily"]["product_key"]) <= products
    assert set(data["fact_gl"]["account_code"]) <= set(data["dim_gl_account"]["account_code"])


def test_date_spine_is_contiguous_and_covers_every_fact_date(data) -> None:
    """2.8 — a gap in the spine silently drops a period from every downstream aggregate."""
    spine = data["dim_date"]
    dates = pd.DatetimeIndex(spine["date"])
    assert dates.min() == pd.Timestamp(C.SPINE_START)
    assert dates.max() == pd.Timestamp(C.SPINE_END)
    assert (dates.to_series().diff().dropna() == pd.Timedelta(days=1)).all()
    assert pd.DatetimeIndex(data["fact_dtc_order_line"]["order_date"]).isin(dates).all()


def test_no_personally_identifiable_information(data) -> None:
    """2.9 — no PII, by design. The repository is public from v0.5-model."""
    for column in data["dim_customer"].columns:
        assert not any(token in column.lower() for token in PII_FIELDS), column


def test_customer_keys_are_stable_across_orders(data) -> None:
    """Cohort analysis needs a customer to be the same customer in every order."""
    orders = data["fact_dtc_order_line"]
    known = set(data["dim_customer"]["customer_key"])
    assert set(orders["customer_key"]) <= known


# --- 2.11 accounting ------------------------------------------------------------------------


def test_trial_balance_is_zero_every_period(data) -> None:
    """2.11 — the strongest single assertion about the ledger."""
    ledger = data["fact_gl"]
    actual = ledger[ledger["version_name"] == "Actual"].copy()
    actual["period"] = pd.to_datetime(actual["date"]).dt.to_period("M")
    by_period = actual.groupby("period")["amount"].sum()
    assert by_period.abs().max() < 0.01, by_period[by_period.abs() > 0.01]


def test_ledger_balances_overall(data) -> None:
    actual = data["fact_gl"]
    actual = actual[actual["version_name"] == "Actual"]
    assert abs(actual["amount"].sum()) < 0.01


# --- 2.16 to 2.19 calibration ----------------------------------------------------------------


@pytest.mark.parametrize("year", C.ACTUAL_YEARS)
def test_net_revenue_hits_target(data, year: int) -> None:
    """2.16 — revenue is measured after stockout suppression and returns."""
    dtc = data["fact_dtc_order_line"]
    ws = data["fact_wholesale_invoice_line"]
    returns = data["fact_return_line"]
    d = dtc[dtc["fiscal_year"] == year]
    w = ws[ws["fiscal_year"] == year]
    sale_year = pd.to_datetime(returns["sale_date"]).dt.year
    r = returns[sale_year == year]
    net = (
        d["net_merchandise_value"].sum()
        + d["shipping_revenue_allocated"].sum()
        + w["net_revenue"].sum()
        - r["refund_amount"].sum()
    )
    target = C.ACTUALS[year].revenue
    assert abs(net / target - 1) < 0.01, f"FY{year} {net:,.0f} vs {target:,.0f}"


@pytest.mark.parametrize("year", C.ACTUAL_YEARS)
def test_channel_mix_hits_target(data, year: int) -> None:
    """2.17 — the mix shift is the central story; it cannot be approximate."""
    dtc = data["fact_dtc_order_line"]
    ws = data["fact_wholesale_invoice_line"]
    d = dtc[dtc["fiscal_year"] == year]
    w = ws[ws["fiscal_year"] == year]
    dtc_net = d["net_merchandise_value"].sum() + d["shipping_revenue_allocated"].sum()
    share = dtc_net / (dtc_net + w["net_revenue"].sum())
    assert abs(share - C.ACTUALS[year].dtc_share) < 0.02


# --- 2.23, 2.24 concentration -------------------------------------------------------------


def test_sku_revenue_concentration(data) -> None:
    """2.23 — top 5 ~38%, top 10 ~55% of revenue (§4.1)."""
    weights = data["dim_product"]["revenue_weight"].sort_values(ascending=False)
    assert abs(weights.iloc[:5].sum() - 0.38) < 0.02
    assert abs(weights.iloc[:10].sum() - 0.55) < 0.02


def test_wholesale_account_concentration(data) -> None:
    """2.24 — largest 24%, top 5 62%. The largest sits just under the 25% covenant cap."""
    weights = data["dim_wholesale_account"]["revenue_weight"].sort_values(ascending=False)
    assert abs(weights.iloc[0] - 0.24) < 0.02
    assert abs(weights.iloc[:5].sum() - 0.62) < 0.02


def test_sku_class_revenue_split(data) -> None:
    products = data["dim_product"]
    by_class = products.groupby("sku_class")["revenue_weight"].sum()
    for sku_class, expected in (("A", 0.55), ("B", 0.30), ("C", 0.15)):
        assert abs(by_class[sku_class] - expected) < 0.02


# --- 2.25, 2.26 behaviour ------------------------------------------------------------------


def test_every_return_follows_its_originating_sale(data) -> None:
    """2.25 — a return before its sale is the clearest possible sign of broken lag logic."""
    returns = data["fact_return_line"]
    assert (
        pd.to_datetime(returns["return_receipt_date"]) >= pd.to_datetime(returns["sale_date"])
    ).all()


def test_return_lag_matches_the_stated_distribution(data) -> None:
    returns = data["fact_return_line"]
    dtc = returns[returns["source"] == "DTC"]
    lag = (pd.to_datetime(dtc["return_receipt_date"]) - pd.to_datetime(dtc["sale_date"])).dt.days
    assert abs(lag.mean() - C.DTC_RETURN_LAG_MEAN) < 3


def test_purchase_order_deposits_precede_receipt(data) -> None:
    """2.26 — the negative effective DPO is the whole cash story (§5.6)."""
    pos = data["fact_purchase_order_line"]
    if pos.empty:
        pytest.skip("no purchase orders")
    assert (pd.to_datetime(pos["deposit_date"]) < pd.to_datetime(pos["actual_receipt_date"])).all()


# --- 2.28 stockouts --------------------------------------------------------------------------


def test_demand_exceeds_realised_where_stock_ran_out(data) -> None:
    """2.28 / check 20 — realised revenue must sit below underlying demand, and the gap must
    split half lost, half deferred. If the two come out equal, the demand gross-up went the
    wrong way and the cost of the stockout has been erased."""
    stock = data["fact_stockout"]
    assert not stock.empty
    assert (stock["suppressed_units"] > 0).all()
    total = stock["suppressed_units"].sum()
    assert abs(stock["lost_units"].sum() / total - C.STOCKOUT_LOST_SHARE) < 0.01
    assert abs(stock["deferred_units"].sum() / total - (1 - C.STOCKOUT_LOST_SHARE)) < 0.01
    assert not data["fact_dtc_suppressed_demand"].empty


def test_hero_stockout_rate_is_near_target(data) -> None:
    products = data["dim_product"]
    hero_keys = set(products.loc[products["is_hero"], "product_key"])
    stock = data["fact_stockout"]
    hero = stock[stock["product_key"].isin(hero_keys)]
    demand = data["fact_inventory_daily"]
    hero_demand = demand[demand["product_key"].isin(hero_keys)]["shipments"].sum()
    rate = hero["suppressed_units"].sum() / (hero_demand + hero["suppressed_units"].sum())
    assert 0.02 < rate < 0.07, rate


# --- 2.29 events ------------------------------------------------------------------------------


def test_april_2025_supplier_cost_step_is_isolated_to_product_cost(data) -> None:
    """2.29 — the step must move product cost only, or the margin bridge cannot attribute it."""
    from bellwether.data.inventory import landed_cost_series

    products = data["dim_product"]
    before = pd.DatetimeIndex([pd.Timestamp("2025-03-01")])
    after = pd.DatetimeIndex([pd.Timestamp("2025-05-01")])
    step = (
        landed_cost_series(products, after).mean() / landed_cost_series(products, before).mean() - 1
    )
    expected = C.SUPPLIER_COST_INCREASE_PCT * C.LANDED_COST_SPLIT["product"]
    assert abs(step - expected) < 0.005


def test_february_2025_launch_cohort_exists(data) -> None:
    """2.30 — the launch has to be identifiable, or its failure cannot be told apart."""
    products = data["dim_product"]
    launch = products[products["lifecycle_state"] == "launch"]
    assert len(launch) >= 4
    assert (pd.to_datetime(launch["launch_date"]) == pd.Timestamp(C.LAUNCH_DATE)).all()


# --- 2.31 to 2.35 financing ---------------------------------------------------------------------


def test_borrowing_base_respects_the_inventory_sublimit() -> None:
    """The $1.0M sublimit binds before the advance rate does at high inventory."""
    base = financing.borrowing_base(receivables=1_000_000, inventory_at_cost=5_000_000)
    assert base["inventory_advance"] == C.INVENTORY_SUBLIMIT


def test_concentration_cap_reduces_eligible_receivables() -> None:
    """Growth in the largest account consumes availability rather than creating it."""
    under = financing.borrowing_base(1_000_000, 500_000, largest_account_share=0.24)
    over = financing.borrowing_base(1_000_000, 500_000, largest_account_share=0.40)
    assert over["eligible_ar"] < under["eligible_ar"]


def test_revolver_never_draws_beyond_the_borrowing_base(data) -> None:
    """2.35 — debt is not a balancing plug (§6.10)."""
    schedule = data["fact_financing_monthly"]
    assert (schedule["revolver_drawn"] <= schedule["borrowing_base"] + 0.01).all()


def test_consolidation_is_the_only_scenario_reaching_breakeven(data) -> None:
    """The four-way comparison only works if exactly one scenario turns profitable."""
    plan = data["fact_forecast_monthly"]
    latest = plan[plan["version_name"] == "Latest Forecast"]
    final = latest[latest["fiscal_year"] == 2028]
    by_scenario = final.groupby("scenario_name")["ebitda"].sum()
    positive = by_scenario[by_scenario > 0]
    assert list(positive.index) == ["Consolidation / Path to Breakeven"], by_scenario.to_dict()


def test_every_version_scenario_combination_is_present(data) -> None:
    """Budget exists under the operating plan only; the rest under all four scenarios."""
    plan = data["fact_forecast_monthly"]
    pairs = set(map(tuple, plan[["version_name", "scenario_name"]].drop_duplicates().to_numpy()))
    assert pairs == set(
        map(tuple, __import__("bellwether.data.forecast", fromlist=["x"]).VERSION_SCENARIOS)
    )
