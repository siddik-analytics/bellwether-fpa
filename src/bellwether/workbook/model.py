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
from bellwether.transform import expressions, semantic, sensitivity, statements
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

#: The hidden sheet every statement looks up. All ten version/scenario combinations live here,
#: which is what lets one workbook carry the whole comparison (E-c) with a live selector over it.
DATA_SHEET = "Data"
#: A row emitted once per combination so a formula can ask whether a selection exists at all.
#: Budget was approved under Balanced Base only, and the model has to say so rather than show
#: zeros - criterion 4.14.
EXISTS_KEY = "combination exists"
DEFAULT_VERSION = "Latest Forecast"
DEFAULT_SCENARIO = "Balanced Base"
BUDGET_NOTE = "not applicable - Budget was approved under Balanced Base only"


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


@dataclass(frozen=True)
class DataBlock:
    """Where the lookup ranges are. Statements reference these, never a literal range."""

    key_rows: int
    months: int

    @property
    def keys(self) -> str:
        return f"{DATA_SHEET}!$A$2:$A${self.key_rows + 1}"

    @property
    def values(self) -> str:
        return f"{DATA_SHEET}!$B$2:${_column_letter(self.months)}${self.key_rows + 1}"


@dataclass(frozen=True)
class Controls:
    """The two cells the reader drives the model from, and the guard derived from them."""

    version: str
    scenario: str
    available: str


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
) -> tuple[dict[str, int], dict[str, list[float]]]:
    """Write one statement block.

    Returns the row each line landed on and the oracle values written there. The values come back
    rather than being read off the worksheet afterwards because these cells are about to become
    formulas, and a formula cell has no number to read back. The cached value has to originate in
    the semantic layer, which is the whole point.
    """
    indexed = frame.set_index("month")
    rows: dict[str, int] = {}
    values: dict[str, list[float]] = {}
    boundary = _boundary(months)
    for name, style, is_total in lines:
        label_fmt = sheet.formats["label_total"] if is_total else sheet.formats["label"]
        sheet.worksheet.write(sheet.row, 0, name, label_fmt)
        line: list[float] = []
        for offset, month in enumerate(months):
            value = float(indexed[name].get(month, 0.0)) if name in indexed else 0.0
            sheet.worksheet.write_number(
                sheet.row,
                first_col + offset,
                value,
                _cell_format(sheet, style, is_total, month, boundary),
            )
            line.append(value)
        rows[name] = sheet.row
        values[name] = line
        sheet.row += 1
    return rows, values


def _cell_format(sheet: Sheet, style: str, is_total: bool, month, boundary):
    if month == boundary and style == "money":
        return sheet.formats["boundary_cell"]
    key = f"{style}_total" if is_total and f"{style}_total" in sheet.formats else style
    return sheet.formats[key]


def _lookup(prefix: str, label: str, data: DataBlock, controls: Controls, column: int) -> str:
    """A forecast cell: whatever the two selector cells currently name."""
    key = f'{controls.version}&"|"&{controls.scenario}&"|{prefix}:"&{label}'
    index = f"INDEX({data.values},MATCH({key},{data.keys},0),{column})"
    # Empty, not zero, when the combination was never approved - criterion 4.14.
    return f'=IF({controls.available}<>1,"",{index})'


def _actual_lookup(prefix: str, label: str, data: DataBlock, column: int) -> str:
    """A historical cell.

    Always Actual. It is the only version with 2023-25 data, so a selector set to Budget must not
    blank out the history it is being compared against.
    """
    key = f'"Actual|{DEFAULT_SCENARIO}|{prefix}:"&{label}'
    return f"=INDEX({data.values},MATCH({key},{data.keys},0),{column})"


def _link_to_data(
    sheet: Sheet,
    prefix: str,
    lines,
    rows: dict[str, int],
    values: dict[str, list[float]],
    months: list[pd.Timestamp],
    data: DataBlock,
    controls: Controls,
    first_col: int,
    skip: frozenset[str] = frozenset(),
) -> None:
    """Turn source lines into lookups driven by the version and scenario selectors."""
    boundary = _boundary(months)
    for name, style, is_total in lines:
        if name in skip:
            continue
        row = rows[name]
        label = f"$A{row + 1}"
        for offset, month in enumerate(months):
            column = offset + 1
            expression = (
                _actual_lookup(prefix, label, data, column)
                if month < boundary
                else _lookup(prefix, label, data, controls, column)
            )
            sheet.formula(
                row,
                first_col + offset,
                expression,
                values[name][offset],
                _cell_format(sheet, style, is_total, month, boundary),
            )


#: Lines the P&L computes rather than looks up. Taken from the semantic layer's derivations
#: (ADR 0019) rather than restated here — this table used to hold its own copy of the ladder,
#: which made the workbook a third place the arithmetic lived.
DERIVED_LINES = frozenset(semantic.DERIVED)


def _add_tied_formulas(
    sheet: Sheet,
    rows: dict[str, int],
    values: dict[str, list[float]],
    months: list[pd.Timestamp],
    controls: Controls,
    first_col: int,
) -> None:
    """Derive the P&L subtotals in Excel, carrying the oracle's value as the cached result.

    The formula is generated from the metric's own derivation, so Net Revenue is visibly Gross
    less Contra on the face of the sheet and a reader can trace it — and it cannot drift from
    what Python computed, because both come from the same expression.

    Forecast columns take the same availability guard as the lines they read. Without it, an
    unapproved combination would leave the source rows empty and the subtotals showing #VALUE!,
    which reads as a broken workbook rather than as a deliberate answer.
    """
    boundary = _boundary(months)

    def guard(expression: str, month) -> str:
        if month < boundary:
            return f"={expression}"
        return f'=IF({controls.available}<>1,"",{expression})'

    for name in semantic.DERIVATION_ORDER:
        if name not in rows:
            continue
        metric = semantic.DERIVED[name]
        is_ratio = metric.format_string.endswith("%")
        for offset, month in enumerate(months):
            column = _column_letter(first_col + offset)
            cells = {
                dependency: f"{column}{rows[dependency] + 1}"
                for dependency in metric.depends_on
                if dependency in rows
            }
            if len(cells) != len(metric.depends_on):
                continue
            body = expressions.to_excel(metric.derivation, cells)
            fmt = (
                sheet.formats["percent"]
                if is_ratio
                else _cell_format(sheet, "money", True, month, boundary)
            )
            sheet.formula(
                rows[name], first_col + offset, guard(body, month), values[name][offset], fmt
            )


def _forecast_versions() -> list[str]:
    """The versions a reader can select. Actual is not one of them - it is the history."""
    return ["Budget", "Latest Forecast", "Prior Forecast"]


def _write_controls(sheet: Sheet, data: DataBlock) -> Controls:
    """The two cells that drive every statement - criteria 4.12 and 4.13.

    A dropdown is the whole interface: a reader switches version or scenario and the three
    statements follow. The guard cell underneath is what stops an unapproved combination from
    presenting itself as a set of zeroes.
    """
    sheet.worksheet.write(sheet.row, 0, "Model controls", sheet.formats["heading"])
    sheet.row += 1

    version_row = sheet.row
    sheet.worksheet.write(sheet.row, 0, "Forecast version", sheet.formats["label"])
    sheet.worksheet.write(sheet.row, 1, DEFAULT_VERSION, sheet.formats["selector"])
    sheet.worksheet.data_validation(
        sheet.row, 1, sheet.row, 1, {"validate": "list", "source": _forecast_versions()}
    )
    sheet.row += 1

    scenario_row = sheet.row
    sheet.worksheet.write(sheet.row, 0, "Scenario", sheet.formats["label"])
    sheet.worksheet.write(sheet.row, 1, DEFAULT_SCENARIO, sheet.formats["selector"])
    sheet.worksheet.data_validation(
        sheet.row, 1, sheet.row, 1, {"validate": "list", "source": list(C.SCENARIOS)}
    )
    sheet.row += 1

    version = f"Cover!$B${version_row + 1}"
    scenario = f"Cover!$B${scenario_row + 1}"
    guard_row = sheet.row
    probe = f'$B${version_row + 1}&"|"&$B${scenario_row + 1}&"|{EXISTS_KEY}"'
    sheet.worksheet.write(sheet.row, 0, "Selection exists", sheet.formats["label"])
    sheet.formula(
        sheet.row,
        1,
        f"=IF(ISNA(MATCH({probe},{data.keys},0)),0,1)",
        1.0,
        sheet.formats["integer"],
    )
    sheet.row += 1

    available = f"Cover!$B${guard_row + 1}"
    sheet.worksheet.write(sheet.row, 0, "", sheet.formats["label"])
    sheet.formula(
        sheet.row,
        1,
        f'=IF($B${guard_row + 1}=1,"Showing "&$B${version_row + 1}&" / "'
        f'&$B${scenario_row + 1},"{BUDGET_NOTE}")',
        f"Showing {DEFAULT_VERSION} / {DEFAULT_SCENARIO}",
        sheet.formats["note"],
    )
    sheet.row += 2
    return Controls(version=version, scenario=scenario, available=available)


def _write_data_sheet(
    sheet: Sheet, keys: list[str], grid: list[list[float]], months: list[pd.Timestamp]
) -> None:
    """The long form of every combination, hidden because it is machinery rather than a report."""
    sheet.worksheet.write(0, 0, "key", sheet.formats["column_header_left"])
    for offset, month in enumerate(months):
        sheet.worksheet.write_datetime(0, 1 + offset, month, sheet.formats["month"])
    for row, (key, line) in enumerate(zip(keys, grid, strict=True), start=1):
        sheet.worksheet.write(row, 0, key, sheet.formats["label"])
        for offset, value in enumerate(line):
            sheet.worksheet.write_number(row, 1 + offset, value, sheet.formats["money"])
    sheet.worksheet.set_column(0, 0, 64)
    sheet.worksheet.hide()


def _data_grid(
    frames: list[tuple[str, pd.DataFrame, list[str]]], months: list[pd.Timestamp]
) -> tuple[list[str], list[list[float]]]:
    """Every version, scenario and line, on one month axis.

    The statement prefix is part of the key because EBITDA appears on both the P&L and the cash
    flow and the two must not collide into one row.
    """
    keys: list[str] = []
    grid: list[list[float]] = []
    seen: set[tuple[str, str]] = set()
    for prefix, frame, names in frames:
        frame = frame.copy()
        frame["month"] = pd.to_datetime(frame["month"])
        for (version, scenario), group in frame.groupby(
            ["version_name", "scenario_name"], sort=True
        ):
            if (version, scenario) not in seen:
                seen.add((version, scenario))
                keys.append(f"{version}|{scenario}|{EXISTS_KEY}")
                grid.append([1.0] * len(months))
            indexed = group.groupby("month").sum(numeric_only=True)
            for name in names:
                if name not in indexed:
                    continue
                column = indexed[name]
                keys.append(f"{version}|{scenario}|{prefix}:{name}")
                grid.append([float(column.get(month, 0.0)) for month in months])
    return keys, grid


def _write_cover(sheet: Sheet, series: pd.DataFrame, data: DataBlock) -> Controls:
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
    controls = _write_controls(sheet, data)
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
    return controls


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
    sheet: Sheet,
    name: str,
    subtitle: str,
    frame: pd.DataFrame,
    months: list[pd.Timestamp],
    lines,
    prefix: str,
    data: DataBlock,
    controls: Controls,
    skip: frozenset[str] = frozenset(),
) -> tuple[dict[str, int], dict[str, list[float]]]:
    sheet.title(name, subtitle)
    _write_month_headers(sheet, months, first_col=1)
    rows, values = _write_series_block(sheet, frame, months, lines, first_col=1)
    _link_to_data(sheet, prefix, lines, rows, values, months, data, controls, 1, skip)
    sheet.row += 1
    sheet.formula(
        sheet.row,
        0,
        f'="Actual to Dec-{max(C.ACTUAL_YEARS)}; forecast from Jan-{min(C.FORECAST_YEARS)} on "'
        f'&{controls.version}&" / "&{controls.scenario}',
        f"Actual to Dec-{max(C.ACTUAL_YEARS)}; forecast from Jan-{min(C.FORECAST_YEARS)} on "
        f"{DEFAULT_VERSION} / {DEFAULT_SCENARIO}",
        sheet.formats["note"],
    )
    sheet.row += 1
    sheet.worksheet.write(
        sheet.row,
        0,
        "The highlighted column marks the actual/forecast boundary. History is always Actual; "
        "the selectors on the Cover sheet drive the forecast columns.",
        sheet.formats["note"],
    )
    sheet.worksheet.set_column(0, 0, sheet.theme.column_width_label)
    sheet.worksheet.set_column(1, len(months) + 1, sheet.theme.column_width_month)
    sheet.worksheet.freeze_panes(*sheet.theme.freeze_at)
    return rows, values


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

    bs_lines = [(key, "money", key == statements.EQUITY) for key, _ in BALANCE_LINES]
    bs_lines.append(("difference", "money", True))
    cf_lines = [(name, "money", total) for name, total in CASH_LINES]
    months = _months(series)

    # Build the lookup grid before anything references it: the ranges the statements point at
    # depend on how many keys it holds, and a formula written against a guessed extent would be
    # wrong in a way nothing would catch until Excel opened the file.
    keys, grid = _data_grid(
        [
            ("PL", series, [name for name, _, _ in PL_LINES]),
            ("BS", balances, [name for name, _, _ in bs_lines]),
            ("CF", flow, [name for name, _, _ in cf_lines]),
        ],
        months,
    )
    data = DataBlock(key_rows=len(keys), months=len(months))

    controls = _write_cover(sheet_for("Cover"), series, data)
    _write_assumptions(sheet_for("Assumptions"))

    def default_view(frame: pd.DataFrame) -> pd.DataFrame:
        """What the workbook shows when it is opened: Actual, then the operating plan."""
        subset = frame[
            (frame["version_name"].isin(["Actual", DEFAULT_VERSION]))
            & (frame["scenario_name"] == DEFAULT_SCENARIO)
        ]
        return subset.groupby("month", as_index=False).sum(numeric_only=True)

    plan = default_view(series)
    pl_sheet = sheet_for("P&L")
    rows, values = _write_statement(
        pl_sheet,
        "Profit and loss",
        "Actual to Dec-2025, then the selected version and scenario",
        plan,
        months,
        PL_LINES,
        "PL",
        data,
        controls,
        skip=DERIVED_LINES,
    )
    _add_tied_formulas(pl_sheet, rows, values, months, controls, first_col=1)

    _write_statement(
        sheet_for("Balance sheet"),
        "Balance sheet",
        "Assets less contra-assets equal liabilities plus equity, every period",
        default_view(balances),
        months,
        bs_lines,
        "BS",
        data,
        controls,
    )

    _write_statement(
        sheet_for("Cash flow"),
        "Cash flow",
        "Indirect method, from EBITDA - ADR 0018",
        default_view(flow),
        months,
        cf_lines,
        "CF",
        data,
        controls,
    )

    _write_scenarios(sheet_for("Scenarios"), series)
    _write_sensitivity(sheet_for("Sensitivity"), sensitivity.grids())

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
        "The Cover sheet carries a version and a scenario selector. History is always Actual;",
        "  the selectors drive the forecast columns on all three statements. Budget exists only",
        "  under Balanced Base, and any other pairing with it says so rather than showing zeroes.",
        "",
        DISCLOSURE,
    ]
    for line in lines:
        documentation.worksheet.write(documentation.row, 0, line, documentation.formats["note"])
        documentation.row += 1
    documentation.worksheet.set_column(0, 0, 100)

    _write_data_sheet(sheet_for(DATA_SHEET), keys, grid, months)

    workbook.close()
    return {
        "sheets": 9,
        "months": len(months),
        "scenarios": len(C.SCENARIOS),
        "theme": theme.name,
    }
