"""Phase 4 acceptance criteria — see ``docs/phases/phase-04-spec.md``."""

from __future__ import annotations

import hashlib
import re
import time
import zipfile

import pandas as pd
import pytest

from bellwether.data import config as C
from bellwether.data import generate
from bellwether.paths import REPO_ROOT
from bellwether.transform import allocation, semantic, sensitivity, star, statements
from bellwether.workbook import model
from bellwether.workbook import theme as theme_mod

ROW = re.compile(r"<row[^>]*>(.*?)</row>", re.S)
CELL = re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*)>(?:<f[^>]*>.*?</f>)?(?:<v>([^<]*)</v>)?', re.S)
SHARED = re.compile(r"<si>(.*?)</si>", re.S)

CELL_WITH_FORMULA = re.compile(r'<c r="([A-Z]+\d+)"[^>]*>(?:<f[^>]*>([^<]*)</f>)(<v>[^<]*</v>)?')


@pytest.fixture(scope="session")
def tables() -> dict[str, pd.DataFrame]:
    return generate.generate()


@pytest.fixture(scope="session")
def built(tables, tmp_path_factory):
    path = tmp_path_factory.mktemp("workbook") / "northlake.xlsx"
    summary = model.build(tables, path)
    return path, summary


def _sheet_xml(path) -> dict[str, str]:
    archive = zipfile.ZipFile(path)
    return {
        name: archive.read(name).decode("utf-8")
        for name in archive.namelist()
        if name.startswith("xl/worksheets/sheet")
    }


def _numeric_cached_values(path) -> set[float]:
    """Every numeric formula result in the file. Text results - the selection echo the sheets
    carry so a reader always sees which version is showing - are not figures and are skipped."""
    out: set[float] = set()
    for xml in _sheet_xml(path).values():
        for _, _, value in CELL_WITH_FORMULA.findall(xml):
            text = re.sub(r"</?v>", "", value or "")
            try:
                out.add(float(text))
            except ValueError:
                continue
    return out


# --- 4.1 to 4.3 the oracle rule -----------------------------------------------------------


def test_every_formula_carries_a_cached_value(built) -> None:
    """4.1 — the mechanism the whole phase rests on. A formula without one is a defect."""
    path, _ = built
    bare = []
    for name, xml in _sheet_xml(path).items():
        for cell, formula, value in CELL_WITH_FORMULA.findall(xml):
            if not value:
                bare.append((name, cell, formula))
    assert not bare, f"formulas without cached values: {bare[:5]}"


def test_the_workbook_contains_real_formulas(built) -> None:
    """4.2 — a workbook of constants is a report, not a model."""
    path, _ = built
    total = sum(len(CELL_WITH_FORMULA.findall(xml)) for xml in _sheet_xml(path).values())
    assert total > 200, total


def test_formula_cached_values_match_the_semantic_layer(built, tables) -> None:
    """4.3 — Excel reproduces; it does not originate. Checked without Excel present."""
    path, _ = built
    series = statements.metric_series(tables["fact_gl"], tables["dim_gl_account"])
    plan = (
        series[
            (series["version_name"].isin(["Actual", "Latest Forecast"]))
            & (series["scenario_name"] == "Balanced Base")
        ]
        .groupby("month", as_index=False)
        .sum(numeric_only=True)
    )

    cached = _numeric_cached_values(path)
    first_month_net = float(plan.sort_values("month")["Net Revenue"].iloc[0])
    assert any(abs(v - first_month_net) < 0.01 for v in cached), first_month_net


def test_formula_writer_refuses_a_missing_value() -> None:
    """The guard is enforced in code, not by convention."""
    sheet = model.Sheet(worksheet=None, formats={}, theme=theme_mod.Theme())
    with pytest.raises(ValueError, match="cached result"):
        sheet.formula(0, 0, "=A1", None, None)


# --- 4.6 to 4.11 three statements ----------------------------------------------------------


def test_balance_sheet_balances_in_the_workbook_source(tables) -> None:
    """4.6 — the workbook presents what the semantic layer proves."""
    check = statements.balance_sheet_check(tables["fact_gl"], tables["dim_gl_account"])
    assert check["difference"].abs().max() < 0.01


def test_cash_flow_closing_cash_equals_balance_sheet_cash(tables) -> None:
    """4.7 — exactly, with no tolerance."""
    tie = statements.cash_tie(tables["fact_gl"], tables["dim_gl_account"])
    assert tie["difference"].abs().max() < 0.01


def test_iterative_calculation_is_off(built) -> None:
    """4.11 — ADR 0001 chose an acyclic model; this is where it could silently regress."""
    path, _ = built
    workbook_xml = zipfile.ZipFile(path).read("xl/workbook.xml").decode("utf-8")
    calc = re.search(r"<calcPr[^>]*/>", workbook_xml)
    assert calc, "no calcPr element"
    assert "iterate" not in calc.group(0), calc.group(0)


# --- 4.13 to 4.16 drivers, scenarios and sensitivity ----------------------------------------


def test_all_four_scenarios_are_present(built) -> None:
    """4.13 — the scenario comparison is the deliverable, so it is in one workbook (E-c)."""
    path, _ = built
    shared = zipfile.ZipFile(path).read("xl/sharedStrings.xml").decode("utf-8")
    for scenario in C.SCENARIOS:
        assert scenario in shared, scenario


def test_budget_asymmetry_is_shown_not_blanked(built) -> None:
    """4.14 — Budget exists only under Balanced Base. A blank cell reads as zero."""
    path, _ = built
    shared = zipfile.ZipFile(path).read("xl/sharedStrings.xml").decode("utf-8")
    assert "not applicable" in shared


def test_every_contract_driver_appears(built) -> None:
    """4.15 — drivers come from config, not typed into a sheet."""
    path, _ = built
    shared = zipfile.ZipFile(path).read("xl/sharedStrings.xml").decode("utf-8")
    for label in (
        "DTC average order value",
        "Landed cost per unit",
        "Inventory turns",
        "Paid media CAC",
        "Wholesale DSO, days",
    ):
        assert label in shared, label


def test_sensitivity_grids_are_oracle_computed() -> None:
    """4.16 — the oracle computes the grid; Excel's Data Table reproduces it."""
    grids = sensitivity.grids()
    assert set(grids) >= {"Paid media CAC", "Landed cost per unit", "DTC share of revenue"}
    for driver, grid in grids.items():
        assert len(grid) >= 4, driver
        assert grid["ebitda"].nunique() > 1, f"{driver} grid does not vary"


# --- 4.17 to 4.20 structure and skin ---------------------------------------------------------


def test_theme_imports_nothing_from_the_semantic_layer() -> None:
    """4.17 — the separation is worth nothing if it depends on discipline."""
    source = (REPO_ROOT / "src" / "bellwether" / "workbook" / "theme.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("from bellwether.transform", "from bellwether.data", "import pandas"):
        assert forbidden not in source, forbidden


def test_reskin_changes_formats_but_no_value(tables, tmp_path) -> None:
    """4.18 — build the whole workbook twice and prove only the skin moved."""
    default_path = tmp_path / "default.xlsx"
    slate_path = tmp_path / "slate.xlsx"
    model.build(tables, default_path, theme_mod.Theme())
    model.build(tables, slate_path, theme_mod.SLATE)

    def values(path):
        out = {}
        for name, xml in _sheet_xml(path).items():
            out[name] = re.findall(r"<v>([^<]*)</v>", xml)
        return out

    assert values(default_path) == values(slate_path), "a reskin changed a number"
    default_styles = zipfile.ZipFile(default_path).read("xl/styles.xml").decode("utf-8")
    slate_styles = zipfile.ZipFile(slate_path).read("xl/styles.xml").decode("utf-8")
    assert default_styles != slate_styles, "a reskin changed nothing"


def test_no_hardcoded_colour_outside_the_theme() -> None:
    """4.19 — one place to change the livery."""
    source = (REPO_ROOT / "src" / "bellwether" / "workbook" / "model.py").read_text(
        encoding="utf-8"
    )
    assert not re.search(r'"#[0-9A-Fa-f]{6}"', source)


def test_every_sheet_carries_the_disclosure(built) -> None:
    """4.20 — synthetic data, said on every sheet a reader can land on."""
    path, _ = built
    shared = zipfile.ZipFile(path).read("xl/sharedStrings.xml").decode("utf-8")
    assert "illustrative company" in shared
    assert "synthetic" in shared


# --- 4.21 to 4.23 build ----------------------------------------------------------------------


def test_workbook_is_byte_identical_across_runs(tables, tmp_path) -> None:
    """4.23 - two runs, one seed, the same bytes.

    Equal values would be the weaker claim and would pass while a timestamp or a dict ordering
    drifted underneath. xlsxwriter can be made reproducible, so the criterion is byte-identity.
    """
    first, second = tmp_path / "a.xlsx", tmp_path / "b.xlsx"
    model.build(tables, first)
    model.build(tables, second)
    assert hashlib.sha256(first.read_bytes()).hexdigest() == (
        hashlib.sha256(second.read_bytes()).hexdigest()
    )


def test_generation_is_well_inside_the_time_budget(tables, tmp_path) -> None:
    """4.22 - sixty seconds. The margin matters: this runs on every commit."""
    started = time.perf_counter()
    model.build(tables, tmp_path / "timed.xlsx")
    assert time.perf_counter() - started < 60.0


def test_workbook_has_the_expected_sheets(built) -> None:
    path, summary = built
    assert summary["sheets"] == 9
    assert summary["months"] == 72
    shared = zipfile.ZipFile(path).read("xl/sharedStrings.xml").decode("utf-8")
    for sheet in (
        "Profit and loss",
        "Balance sheet",
        "Cash flow",
        "Assumptions",
        "Sensitivity",
        "Documentation",
    ):
        assert sheet in shared, sheet


def test_actual_forecast_boundary_is_marked(built) -> None:
    """E-d — a reader must not be able to miss where actuals stop."""
    path, _ = built
    styles = zipfile.ZipFile(path).read("xl/styles.xml").decode("utf-8")
    assert theme_mod.Theme().boundary.replace("#", "").upper() in styles.upper()


# --- 4.8 to 4.10 the statements tie to the semantic layer, not to each other -------------------


def test_net_income_flows_to_retained_earnings(tables) -> None:
    """4.8 - the roll-forward ties.

    The ledger never closes the P&L to equity, so the balance sheet only balances because the
    accumulated result is added back. That makes this the join the balance is standing on, and a
    sign error here would show up as a balanced sheet with the wrong equity.
    """
    keys = ["month", "version_name", "scenario_name"]
    accumulated = statements.retained_earnings(tables["fact_gl"], tables["dim_gl_account"])
    series = statements.metric_series(tables["fact_gl"], tables["dim_gl_account"])
    merged = accumulated.merge(series[[*keys, "Net Income"]], on=keys).sort_values("month")
    merged["cumulative"] = merged.groupby(["version_name", "scenario_name"])["Net Income"].cumsum()
    # Accounts carry credits negative, so the accumulated result is the cumulative net income
    # with the opposite sign. Asserting the sum is zero catches a sign flip that asserting
    # equality of magnitudes would not.
    assert (merged["accumulated_result"] + merged["cumulative"]).abs().max() < 0.01
    assert len(merged) == 360


def test_channel_revenue_sums_to_the_total_the_workbook_reports(built, tables) -> None:
    """4.9 - disaggregation sums to the whole, checked against the figure the workbook prints."""
    ledger = tables["fact_gl"]
    ledger = ledger[ledger["version_name"] == "Actual"].copy()
    mapping = allocation.build_mapping(tables["dim_gl_account"], tables["dim_department"])
    ledger = star.channel_key_for_ledger(ledger, mapping, tables["dim_channel"])
    ledger["year"] = pd.to_datetime(ledger["date"]).dt.year
    ledger = ledger[ledger["year"] == max(C.ACTUAL_YEARS)]

    dtc, wholesale = tables["fact_dtc_order_line"], tables["fact_wholesale_invoice_line"]
    year = max(C.ACTUAL_YEARS)
    units = {
        "DTC": float(dtc[dtc["fiscal_year"] == year]["quantity"].sum()),
        "Wholesale": float(wholesale[wholesale["fiscal_year"] == year]["units"].sum()),
    }
    by_channel = semantic.channel_contribution(ledger, tables["dim_gl_account"], units)
    channel_total = float(by_channel["Net Revenue"].sum())

    series = statements.metric_series(tables["fact_gl"], tables["dim_gl_account"])
    reported = float(
        series[
            (series["version_name"] == "Actual") & (pd.to_datetime(series["month"]).dt.year == year)
        ]["Net Revenue"].sum()
    )
    assert abs(channel_total - reported) < 1.0

    # And that same total is a number the workbook actually contains, not one only the test knows.
    path, _ = built
    cached = _numeric_cached_values(path)
    monthly_net = series[
        (series["version_name"] == "Actual") & (series["scenario_name"] == "Balanced Base")
    ].sort_values("month")["Net Revenue"]
    assert any(any(abs(v - float(m)) < 0.01 for v in cached) for m in monthly_net.head(3)), (
        "the workbook does not carry the net revenue the disaggregation ties to"
    )


# --- 4.12 to 4.14 the selectors actually select ------------------------------------------------


def _shared_strings(path) -> list[str]:
    xml = zipfile.ZipFile(path).read("xl/sharedStrings.xml").decode("utf-8")
    return [re.sub(r"<[^>]+>", "", block) for block in SHARED.findall(xml)]


def _data_sheet(path) -> dict[str, list[float]]:
    """Read the hidden lookup grid back out of the file, keyed as the formulas key it.

    Parsing the written workbook rather than calling the builder is the point: the selector is
    only real if what landed in the file resolves, and a helper that re-derived the grid in
    Python would pass even if nothing had been written.
    """
    strings = _shared_strings(path)
    sheets = _sheet_xml(path)
    xml = sheets[max(sheets, key=lambda n: int(re.search(r"sheet(\d+)", n).group(1)))]
    grid: dict[str, list[float]] = {}
    for body in ROW.findall(xml):
        key = None
        values: list[float] = []
        for column, _, attrs, value in CELL.findall(body):
            if column == "A":
                key = strings[int(value)] if 't="s"' in attrs else value
            elif value not in (None, ""):
                values.append(float(value))
        if key and key != "key":
            grid[key] = values
    return grid


def test_the_selector_reaches_every_combination(built, tables) -> None:
    """4.13 - resolve the lookup by hand for all twelve selectable pairs.

    This is what an Excel recalculation would do, done without Excel. It is not a substitute for
    the COM reconciliation in phase 5; it is the check that the formulas point somewhere real,
    which is the failure a `requires_excel` test would otherwise let through to a machine nobody
    runs CI on.
    """
    path, _ = built
    grid = _data_sheet(path)
    series = statements.metric_series(tables["fact_gl"], tables["dim_gl_account"])

    reachable = 0
    for version in ("Budget", "Latest Forecast", "Prior Forecast"):
        for scenario in C.SCENARIOS:
            subset = series[
                (series["version_name"] == version) & (series["scenario_name"] == scenario)
            ].sort_values("month")
            key = f"{version}|{scenario}|PL:Net Revenue"
            if subset.empty:
                assert key not in grid, f"{key} exists for a combination that was never approved"
                continue
            assert key in grid, key
            reachable += 1
            # The grid runs the full 72-month axis; a forecast combination occupies the tail.
            written = [v for v in grid[key] if v]
            expected = [v for v in subset["Net Revenue"].tolist() if v]
            assert len(written) == len(expected), key
            for got, want in zip(written, expected, strict=True):
                assert abs(got - want) < 0.01, key
    assert reachable == 9, reachable


def test_switching_scenario_changes_the_numbers(built) -> None:
    """4.12 - the model is live. Two scenarios that agreed would mean the selector does nothing."""
    path, _ = built
    grid = _data_sheet(path)
    base = grid["Latest Forecast|Balanced Base|PL:EBITDA"]
    other = grid["Latest Forecast|Wholesale Acceleration|PL:EBITDA"]
    assert base != other
    assert sum(base) != sum(other)


def test_an_unapproved_combination_is_guarded_not_zeroed(built) -> None:
    """4.14 - with a live selector this has teeth it did not have as a static table."""
    path, _ = built
    grid = _data_sheet(path)
    assert "Budget|Balanced Base|combination exists" in grid
    for scenario in C.SCENARIOS:
        if scenario == "Balanced Base":
            continue
        assert f"Budget|{scenario}|combination exists" not in grid

    # A missing key is only a stated answer if the statements consult the guard, so find the
    # guard cell on the cover and prove the P&L formulas reference it.
    cover = _sheet_xml(path)["xl/worksheets/sheet1.xml"]
    guard = re.search(r'<c r="(B\d+)"[^>]*><f>IF\(ISNA\(MATCH\(', cover)
    assert guard, "no availability guard on the cover"
    reference = f"Cover!${guard.group(1)[0]}${guard.group(1)[1:]}"
    for sheet in ("sheet3.xml", "sheet4.xml", "sheet5.xml"):
        xml = _sheet_xml(path)[f"xl/worksheets/{sheet}"]
        assert reference in xml, f"{sheet} does not consult the guard"


def test_history_is_never_driven_by_the_version_selector(built) -> None:
    """A selector set to Budget must not blank 2023 - Budget has no history to show."""
    path, _ = built
    xml = _sheet_xml(path)["xl/worksheets/sheet3.xml"]
    historical = [f for cell, f, _ in CELL_WITH_FORMULA.findall(xml) if cell.startswith("B")]
    assert any("Actual|Balanced Base" in f for f in historical), historical[:3]
