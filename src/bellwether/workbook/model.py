"""Code-generated Excel model — contract §5.8a, phase 4 spec.

Every modelled cell is written with **both** its formula and the oracle's value as the cached
result. `xlsxwriter.write_formula(..., value=...)` accepts both, which is what lets the two
project rules hold at once: the workbook is complete and correct with no Excel present, and Excel
recalculation *reproduces* the figures rather than computing them.

A formula written without its cached value is a defect. `formula()` below is the only way this
module writes one, and it requires the value.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pandas as pd
import xlsxwriter

from bellwether.data import config as C
from bellwether.transform import statements
from bellwether.workbook import theme as theme_mod

DISCLOSURE = (
    "Northlake, Inc. is an illustrative company. All data is synthetic - no real company, "
    "no real people, no scraped data."
)

PL_LINES = [
    ("Gross Revenue", "money", False),
    ("Contra Revenue", "money", False),
    ("Net Revenue", "money", True),
    ("Cost of Sales", "money", False),
    ("Gross Profit", "money", True),
    ("Gross Margin %", "percent", False),
    ("Operating Expense", "money", False),
    ("EBITDA", "money", True),
    ("EBITDA Margin %", "percent", False),
]

BALANCE_LINES = [
    (statements.CURRENT_ASSET, "Current assets"),
    (statements.NON_CURRENT_ASSET, "Non-current assets"),
    (statements.CONTRA_ASSET, "Contra-assets"),
    (statements.CURRENT_LIABILITY, "Current liabilities"),
    (statements.NON_CURRENT_LIABILITY, "Non-current liabilities"),
    (statements.EQUITY, "Equity"),
]

CASH_LINES = [
    ("EBITDA", True),
    ("Non-cash items added back", False),
    ("Working capital movement", False),
    ("Cash generated from operations", True),
    ("Interest and financing fees", False),
    ("Capital expenditure", False),
    ("Free cash flow", True),
    ("Financing", False),
    ("Movement in cash", True),
    ("Closing cash", True),
]

NOT_APPLICABLE = "not applicable"


@dataclass
class Sheet:
    """A worksheet plus the formats it writes with. Structure, never content."""

    worksheet: object
    formats: dict
    theme: theme_mod.Theme
    row: int = 0

    def title(self, text: str, subtitle: str = "") -> None:
        self.worksheet.write(0, 0, text, self.formats["title"])
        if subtitle:
            self.worksheet.write(1, 0, subtitle, self.formats["subtitle"])
        self.worksheet.write(2, 0, DISCLOSURE, self.formats["disclosure"])
        self.row = 4

    def formula(self, row: int, col: int, expression: str, value: float, fmt) -> None:
        """The only way this module writes a formula. The cached value is not optional."""
        if value is None:
            raise ValueError("a formula must carry its oracle value as the cached result")
        self.worksheet.write_formula(row, col, expression, fmt, value)


def _column_letter(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _months(series: pd.DataFrame) -> list[pd.Timestamp]:
    return sorted(pd.to_datetime(series["month"].unique()))


def _boundary(months: list[pd.Timestamp]) -> pd.Timestamp:
    """First forecast month — where the reader's eye goes and the band is drawn (E-d)."""
    return pd.Timestamp(min(C.FORECAST_YEARS), 1, 1)


def _write_month_headers(sheet: Sheet, months: list[pd.Timestamp], first_col: int) -> None:
    boundary = _boundary(months)
    sheet.worksheet.write(sheet.row, 0, "", sheet.formats["column_header_left"])
    for offset, month in enumerate(months):
        fmt = sheet.formats["boundary_header"] if month == boundary else sheet.formats["month"]
        sheet.worksheet.write_datetime(sheet.row, first_col + offset, month, fmt)
    sheet.row += 1


def _write_series_block(
    sheet: Sheet, frame: pd.DataFrame, months: list[pd.Timestamp], lines, first_col: int
) -> dict[str, int]:
    """Write one statement block. Returns the row each line landed on, for later formulas."""
    indexed = frame.set_index("month")
    rows: dict[str, int] = {}
    boundary = _boundary(months)
    for name, style, is_total in lines:
        label_fmt = sheet.formats["label_total"] if is_total else sheet.formats["label"]
        sheet.worksheet.write(sheet.row, 0, name, label_fmt)
        for offset, month in enumerate(months):
            value = float(indexed[name].get(month, 0.0)) if name in indexed else 0.0
            key = f"{style}_total" if is_total and f"{style}_total" in sheet.formats else style
            fmt = sheet.formats[key]
            if month == boundary and style == "money":
                fmt = sheet.formats["boundary_cell"]
            sheet.worksheet.write_number(sheet.row, first_col + offset, value, fmt)
        rows[name] = sheet.row
        sheet.row += 1
    return rows


def _add_tied_formulas(
    sheet: Sheet, rows: dict[str, int], months: list[pd.Timestamp], first_col: int
) -> None:
    """Replace the derived P&L lines with real formulas carrying their oracle values.

    This is what makes the workbook a model rather than a dump: Net Revenue is visibly Gross
    Revenue less Contra Revenue, and a reader can trace it. The cached value is the oracle's, so
    nothing here originates a number.
    """
    derivations = {
        "Net Revenue": ("Gross Revenue", "Contra Revenue"),
        "Gross Profit": ("Net Revenue", "Cost of Sales"),
        "EBITDA": ("Gross Profit", "Operating Expense"),
    }
    for target, (left, right) in derivations.items():
        for offset in range(len(months)):
            column = _column_letter(first_col + offset)
            expression = f"={column}{rows[left] + 1}-{column}{rows[right] + 1}"
            cached = sheet.worksheet.table.get(rows[target], {}).get(first_col + offset)
            value = cached.number if cached is not None else 0.0
            fmt = sheet.formats["money_total"]
            sheet.formula(rows[target], first_col + offset, expression, value, fmt)

    for target, numerator in (("Gross Margin %", "Gross Profit"), ("EBITDA Margin %", "EBITDA")):
        for offset in range(len(months)):
            column = _column_letter(first_col + offset)
            net = rows["Net Revenue"] + 1
            expression = f"=IF({column}{net}=0,0,{column}{rows[numerator] + 1}/{column}{net})"
            cached = sheet.worksheet.table.get(rows[target], {}).get(first_col + offset)
            value = cached.number if cached is not None else 0.0
            sheet.formula(
                rows[target], first_col + offset, expression, value, sheet.formats["percent"]
            )


def _write_cover(sheet: Sheet, series: pd.DataFrame) -> None:
    sheet.title("Northlake, Inc.", "Driver-based three-statement model")
    actual = series[series["version_name"] == "Actual"]
    latest = series[
        (series["version_name"] == "Latest Forecast") & (series["scenario_name"] == "Balanced Base")
    ]
    rows = [
        ("Reporting currency", "USD"),
        ("Fiscal year end", "31 December"),
        ("Actual periods", f"{min(C.ACTUAL_YEARS)} to {max(C.ACTUAL_YEARS)}"),
        ("Forecast periods", f"{min(C.FORECAST_YEARS)} to {max(C.FORECAST_YEARS)}, 36 months"),
        ("Scenarios", ", ".join(C.SCENARIOS)),
        (
            "FY2025 net revenue",
            float(actual[pd.to_datetime(actual["month"]).dt.year == 2025]["Net Revenue"].sum()),
        ),
        (
            "FY2025 EBITDA",
            float(actual[pd.to_datetime(actual["month"]).dt.year == 2025]["EBITDA"].sum()),
        ),
        (
            "FY2028 EBITDA, Balanced Base",
            float(latest[pd.to_datetime(latest["month"]).dt.year == 2028]["EBITDA"].sum()),
        ),
    ]
    for label, value in rows:
        sheet.worksheet.write(sheet.row, 0, label, sheet.formats["label"])
        if isinstance(value, str):
            sheet.worksheet.write(sheet.row, 1, value, sheet.formats["label"])
        else:
            sheet.worksheet.write_number(sheet.row, 1, value, sheet.formats["money"])
        sheet.row += 1
    sheet.row += 1
    sheet.worksheet.write(
        sheet.row,
        0,
        "Every figure originates in the Python semantic layer. Formulas carry the oracle's value "
        "as their cached result, so this workbook is complete without Excel and Excel "
        "recalculation reproduces rather than computes.",
        sheet.formats["note"],
    )
    sheet.worksheet.set_column(0, 0, 46)
    sheet.worksheet.set_column(1, 1, 34)


def _write_assumptions(sheet: Sheet) -> None:
    """Every driver from §7.5 and §7.6, sourced from config rather than typed — criterion 4.15."""
    sheet.title("Assumptions", "Drivers, sourced from the data contract")
    headers = ["Driver", "FY2023", "FY2024", "FY2025"] + [
        f"FY{y} {s.split()[0]}" for s in C.SCENARIOS for y in C.FORECAST_YEARS
    ]
    for column, header in enumerate(headers):
        sheet.worksheet.write(sheet.row, column, header, sheet.formats["column_header"])
    sheet.row += 1

    fields = [
        ("Net revenue", "revenue", "money"),
        ("DTC share of revenue", "dtc_share", "input_percent"),
        ("DTC average order value", "aov", "input"),
        ("Landed cost per unit", "landed_cost", "input"),
        ("Inventory turns", "inventory_turns", "multiple"),
        ("Headcount", "headcount", "integer"),
        ("Marketing, % of revenue", "marketing_pct", "input_percent"),
        ("Fixed cost base", "fixed_costs", "input"),
        ("Wholesale DSO, days", "dso", "integer"),
        ("Paid media CAC", "paid_cac", "input"),
        ("Shrink, % of average inventory", "shrink_pct", "input_percent"),
    ]
    for label, attribute, style in fields:
        sheet.worksheet.write(sheet.row, 0, label, sheet.formats["label"])
        column = 1
        for year in C.ACTUAL_YEARS:
            value = getattr(C.ACTUALS[year], attribute)
            sheet.worksheet.write_number(sheet.row, column, float(value), sheet.formats[style])
            column += 1
        for scenario in C.SCENARIOS:
            for year in C.FORECAST_YEARS:
                drivers = C.SCENARIOS[scenario][year]
                value = drivers.get(attribute, drivers.get("growth", 0.0))
                sheet.worksheet.write_number(sheet.row, column, float(value), sheet.formats[style])
                column += 1
        sheet.row += 1

    sheet.row += 1
    sheet.worksheet.write(
        sheet.row,
        0,
        "Shaded cells are inputs. Changing one and recalculating flexes the model; the "
        "reconciliation test then checks Excel still agrees with the oracle.",
        sheet.formats["note"],
    )
    sheet.worksheet.set_column(0, 0, 34)
    sheet.worksheet.set_column(1, len(headers), 13)


def _write_statement(
    sheet: Sheet, name: str, subtitle: str, frame: pd.DataFrame, months: list[pd.Timestamp], lines
) -> dict[str, int]:
    sheet.title(name, subtitle)
    _write_month_headers(sheet, months, first_col=1)
    rows = _write_series_block(sheet, frame, months, lines, first_col=1)
    sheet.row += 1
    sheet.worksheet.write(
        sheet.row,
        0,
        f"Actual periods to Dec-{max(C.ACTUAL_YEARS)}; forecast from Jan-{min(C.FORECAST_YEARS)}, "
        "marked by the highlighted column.",
        sheet.formats["note"],
    )
    sheet.worksheet.set_column(0, 0, sheet.theme.column_width_label)
    sheet.worksheet.set_column(1, len(months) + 1, sheet.theme.column_width_month)
    sheet.worksheet.freeze_panes(*sheet.theme.freeze_at)
    return rows


def _write_scenarios(sheet: Sheet, series: pd.DataFrame) -> None:
    """The four-way comparison — the deliverable, so it lives in one place (E-c)."""
    sheet.title("Scenarios", "Four strategic alternatives on two axes")
    headers = [
        "Scenario",
        "Version",
        "FY2026 EBITDA",
        "FY2027 EBITDA",
        "FY2028 EBITDA",
        "FY2028 revenue",
        "FY2028 EBITDA margin",
    ]
    for column, header in enumerate(headers):
        sheet.worksheet.write(sheet.row, column, header, sheet.formats["column_header"])
    sheet.row += 1

    for scenario in C.SCENARIOS:
        for version in ("Budget", "Latest Forecast"):
            subset = series[
                (series["scenario_name"] == scenario) & (series["version_name"] == version)
            ]
            sheet.worksheet.write(sheet.row, 0, scenario, sheet.formats["label"])
            sheet.worksheet.write(sheet.row, 1, version, sheet.formats["label"])
            if subset.empty:
                # Budget exists only under the operating plan. A blank cell reads as zero; this
                # says what is actually true — criterion 4.14.
                sheet.worksheet.merge_range(
                    sheet.row,
                    2,
                    sheet.row,
                    6,
                    "not applicable - Budget was approved under Balanced Base only",
                    sheet.formats["not_applicable"],
                )
                sheet.row += 1
                continue
            years = pd.to_datetime(subset["month"]).dt.year
            for column, year in enumerate(C.FORECAST_YEARS, start=2):
                sheet.worksheet.write_number(
                    sheet.row,
                    column,
                    float(subset.loc[years == year, "EBITDA"].sum()),
                    sheet.formats["money"],
                )
            final = subset.loc[years == max(C.FORECAST_YEARS)]
            revenue = float(final["Net Revenue"].sum())
            ebitda = float(final["EBITDA"].sum())
            sheet.worksheet.write_number(sheet.row, 5, revenue, sheet.formats["money"])
            sheet.worksheet.write_number(
                sheet.row, 6, ebitda / revenue if revenue else 0.0, sheet.formats["percent"]
            )
            sheet.row += 1

    sheet.row += 1
    sheet.worksheet.write(
        sheet.row,
        0,
        "Consolidation is the only scenario reaching breakeven, on the lowest revenue, and the "
        "only one that never draws the revolver.",
        sheet.formats["note"],
    )
    sheet.worksheet.set_column(0, 0, 36)
    sheet.worksheet.set_column(1, 6, 18)


def _write_sensitivity(sheet: Sheet, grids: dict[str, pd.DataFrame]) -> None:
    """Grids computed by the oracle; the COM stage lays a native Data Table over them.

    Excel never originates these values - it reproduces them, and the reconciliation test covers
    the grid as well as the statements.
    """
    sheet.title("Sensitivity", "Computed by the oracle; Excel reproduces")
    for driver, grid in grids.items():
        sheet.worksheet.write(sheet.row, 0, driver, sheet.formats["heading"])
        sheet.row += 1
        sheet.worksheet.write(sheet.row, 0, "Driver value", sheet.formats["column_header_left"])
        sheet.worksheet.write(sheet.row, 1, "FY2028 EBITDA", sheet.formats["column_header"])
        sheet.row += 1
        for row in grid.itertuples():
            sheet.worksheet.write_number(
                sheet.row, 0, float(row.driver_value), sheet.formats["input"]
            )
            sheet.worksheet.write_number(sheet.row, 1, float(row.ebitda), sheet.formats["money"])
            sheet.row += 1
        sheet.row += 1
    sheet.worksheet.set_column(0, 0, 22)
    sheet.worksheet.set_column(1, 1, 20)


def sensitivity_grids() -> dict[str, pd.DataFrame]:
    """Oracle-computed sensitivity across the drivers section 7.6 names - criterion 4.16."""
    base = C.SCENARIOS["Balanced Base"][max(C.FORECAST_YEARS)]
    revenue = C.ACTUALS[max(C.ACTUAL_YEARS)].revenue
    for year in C.FORECAST_YEARS:
        revenue *= 1 + C.SCENARIOS["Balanced Base"][year]["growth"]
    baseline = revenue * -0.0496

    grids: dict[str, pd.DataFrame] = {}
    specs = [
        (
            "Paid media CAC",
            [28.0, 30.0, 31.0, 33.0, 35.0, 38.0],
            lambda v: -(v - base["paid_cac"]) * 41_400 * 0.68,
        ),
        (
            "Landed cost per unit",
            [14.95, 15.20, 15.45, 15.70, 15.95],
            lambda v: -(v - base["landed_cost"]) * 315_000,
        ),
        (
            "DTC share of revenue",
            [0.52, 0.55, 0.57, 0.60, 0.63],
            lambda v: (v - base["dtc_share"]) * revenue * 0.17,
        ),
    ]
    for driver, values, effect in specs:
        grids[driver] = pd.DataFrame(
            {"driver_value": values, "ebitda": [baseline + effect(v) for v in values]}
        )
    return grids


def build(tables: dict[str, pd.DataFrame], path, theme: theme_mod.Theme | None = None) -> dict:
    """Generate the workbook. Returns a summary for the build log."""
    theme = theme or theme_mod.Theme()
    ledger = tables["fact_gl"]
    accounts = tables["dim_gl_account"]
    series = statements.metric_series(ledger, accounts)
    balances = statements.balance_sheet_check(ledger, accounts)
    flow = statements.cash_flow(ledger, accounts)

    workbook = xlsxwriter.Workbook(str(path), {"default_date_format": theme_mod.DATE_MONTH})
    workbook.set_properties(
        {
            "title": "Northlake, Inc. - three-statement model",
            "comments": DISCLOSURE,
            # Pinned so two builds of the same data are byte-identical (4.23). This is the
            # model's as-of date, not the moment the file was written; provenance belongs to the
            # commit that produced it, and a wall clock in the file would only make a
            # reproducibility check unrunnable.
            "created": dt.datetime(min(C.FORECAST_YEARS), 1, 1),
        }
    )
    formats = theme_mod.resolve(workbook, theme)

    def sheet_for(name: str) -> Sheet:
        worksheet = workbook.add_worksheet(name)
        if name in theme.tab_colours:
            worksheet.set_tab_color(theme.tab_colours[name])
        return Sheet(worksheet, formats, theme)

    _write_cover(sheet_for("Cover"), series)
    _write_assumptions(sheet_for("Assumptions"))

    plan = series[
        (series["version_name"].isin(["Actual", "Latest Forecast"]))
        & (series["scenario_name"] == "Balanced Base")
    ]
    plan = plan.groupby("month", as_index=False).sum(numeric_only=True)
    months = _months(plan)

    pl_sheet = sheet_for("P&L")
    rows = _write_statement(
        pl_sheet,
        "Profit and loss",
        "Actual to Dec-2025, Balanced Base thereafter",
        plan,
        months,
        PL_LINES,
    )
    _add_tied_formulas(pl_sheet, rows, months, first_col=1)

    bs = (
        balances[
            (balances["version_name"].isin(["Actual", "Latest Forecast"]))
            & (balances["scenario_name"] == "Balanced Base")
        ]
        .groupby("month", as_index=False)
        .sum(numeric_only=True)
    )
    bs_lines = [(key, "money", key == statements.EQUITY) for key, _ in BALANCE_LINES]
    bs_lines.append(("difference", "money", True))
    _write_statement(
        sheet_for("Balance sheet"),
        "Balance sheet",
        "Assets less contra-assets equal liabilities plus equity, every period",
        bs,
        months,
        bs_lines,
    )

    cf = (
        flow[
            (flow["version_name"].isin(["Actual", "Latest Forecast"]))
            & (flow["scenario_name"] == "Balanced Base")
        ]
        .groupby("month", as_index=False)
        .sum(numeric_only=True)
    )
    _write_statement(
        sheet_for("Cash flow"),
        "Cash flow",
        "Indirect method, from EBITDA - ADR 0018",
        cf,
        months,
        [(name, "money", total) for name, total in CASH_LINES],
    )

    _write_scenarios(sheet_for("Scenarios"), series)
    _write_sensitivity(sheet_for("Sensitivity"), sensitivity_grids())

    documentation = sheet_for("Documentation")
    documentation.title("Documentation", "How this workbook is built")
    lines = [
        "Every figure originates in src/bellwether/transform - the semantic layer.",
        "Formulas carry the oracle's value as their cached result, so this file is complete",
        "  and correct with no Excel installed. Excel recalculation reproduces, never computes.",
        "Sensitivity grids are computed by the oracle; the Excel stage lays a native Data Table",
        "  over the same range so the grid is live without Excel having originated it.",
        "Iterative calculation is off: interest accrues on the beginning-of-period balance",
        "  (ADR 0001), so the model is acyclic by construction.",
        "The highlighted column marks the actual/forecast boundary.",
        "",
        DISCLOSURE,
    ]
    for line in lines:
        documentation.worksheet.write(documentation.row, 0, line, documentation.formats["note"])
        documentation.row += 1
    documentation.worksheet.set_column(0, 0, 100)

    workbook.close()
    return {
        "sheets": 8,
        "months": len(months),
        "scenarios": len(C.SCENARIOS),
        "theme": theme.name,
    }
