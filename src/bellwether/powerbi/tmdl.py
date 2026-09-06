"""TMDL generation — the semantic model as text that diffs in git.

Every measure here is produced from a ``Metric`` in ``transform/semantic.py``. Base metrics
become one filtered aggregation over ``fact_metric``; derived metrics become their own
derivation, verbatim, because the derivation language *is* DAX reference syntax (ADR 0019).

The rule this package exists to enforce, from ``.claude/rules/powerbi-pbip.md``: **Power BI does
not invent business logic.** Concretely, no measure may name an account code, an account type,
a department or an allocation rule — those are the semantic layer's vocabulary, and their
appearance in DAX would mean the definition now lives in two places. Criterion 5.12 greps for
exactly that.
"""

from __future__ import annotations

import json
import pathlib
import re

import pandas as pd

from bellwether.transform import expressions, semantic

PROJECT = "northlake"
MEASURE_TABLE = "Measures"

#: Where the star lives, relative to the repository root. An absolute path would embed the
#: machine that generated the project into a committed text file, breaking both portability and
#: the byte-for-byte regeneration criterion 5.29 asserts.
RELATIVE_STAR = "data/star"

#: Columns are presented in business language: no underscores, no source-system names.
#: ``sourceColumn`` keeps the physical name, so this is a presentation layer rather than a
#: rename that would have to be matched anywhere else.
COLUMN_NAMES: dict[str, str] = {
    "account_code": "Account code",
    "account_name": "Account",
    "account_type": "Account type",
    "amount": "Amount",
    "channel_allocation": "Channel",
    "channel_name": "Channel",
    "date": "Date",
    "department_name": "Department",
    "description": "Description",
    "display_folder": "Display folder",
    "format_string": "Format string",
    "is_cost": "Is cost",
    "memo": "Memo",
    "metric_name": "Metric",
    "month": "Month",
    "name": "Metric",
    "scenario_name": "Scenario",
    "split_basis": "Attribution basis",
    "value": "Value",
    "version_name": "Version",
}


def column_name(physical: str) -> str:
    """The name a report author sees. Falls back to a title-cased form of the source column."""
    return COLUMN_NAMES.get(physical, physical.replace("_", " ").capitalize())


#: Star tables the model loads. Facts narrow, dimensions wide, no snowflaking.
MODEL_TABLES: tuple[str, ...] = (
    "fact_metric",
    "fact_gl",
    "dim_date",
    "dim_version",
    "dim_scenario",
    "dim_channel",
    "dim_gl_account",
    "dim_department",
    "dim_metric",
)

#: Single-direction, many-to-one. Bi-directional filtering needs an ADR — none is warranted.
RELATIONSHIPS: tuple[tuple[str, str, str, str], ...] = (
    ("fact_metric", "month", "dim_date", "date"),
    ("fact_metric", "metric_name", "dim_metric", "name"),
    ("fact_metric", "version_name", "dim_version", "version_name"),
    ("fact_metric", "scenario_name", "dim_scenario", "scenario_name"),
    ("fact_metric", "channel_allocation", "dim_channel", "channel_name"),
    ("fact_gl", "date", "dim_date", "date"),
    ("fact_gl", "version_name", "dim_version", "version_name"),
    ("fact_gl", "scenario_name", "dim_scenario", "scenario_name"),
    ("fact_gl", "channel_allocation", "dim_channel", "channel_name"),
    ("fact_gl", "account_code", "dim_gl_account", "account_code"),
)

#: Prefix-matched, longest first — see ``_data_type``.
DATA_TYPES = {
    "datetime64": "dateTime",
    "float": "double",
    "int": "int64",
    "bool": "boolean",
}

#: The variance convention, stated once and followed everywhere — rules file, §9 check 24.
VARIANCE_HEADER = (
    "/// Favourable variance is positive whether the line is revenue or cost. The direction "
    "comes from Metric.is_cost in the semantic layer, never from a judgement made here."
)

#: `.claude/rules/powerbi-pbip.md` fixes both the count and the order.
PAGES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "Executive summary",
        "Where the business is, and which plan is fundable",
        ("Net Revenue", "EBITDA", "EBITDA Margin %"),
    ),
    (
        "P&L detail",
        "The gross-to-net ladder, by month and version",
        ("Gross Revenue", "Contra Revenue", "Net Revenue", "Cost of Sales", "Gross Profit"),
    ),
    (
        "Cash and working capital",
        "Where the cash went, and what the facility advances against",
        ("EBITDA", "Net Income"),
    ),
    (
        "Unit economics",
        "Contribution by channel, with corporate shown once and undivided",
        ("Contribution Profit", "Gross Margin %"),
    ),
)


def _data_type(series: pd.Series) -> str:
    """Map a pandas dtype to a TMDL one.

    Matched by prefix rather than by exact string: pandas reports datetime resolution in the
    dtype (``datetime64[us]``, ``datetime64[s]``), and an exact lookup silently made every date
    column a string — which would have cost the date table its Time category and all time
    intelligence with it.
    """
    dtype = str(series.dtype)
    for prefix, tmdl_type in DATA_TYPES.items():
        if dtype.startswith(prefix):
            return tmdl_type
    return "string"


def _summarize_by(column: str, series: pd.Series) -> str:
    """Never let Power BI implicitly sum a column that is not a measure.

    An implicit measure is an invented one, and a summarised key or boolean is worse than
    useless — a "Sum of Is promotional" is a number with no meaning that a report author will
    eventually put on a slide.
    """
    if _data_type(series) in {"string", "dateTime", "boolean"}:
        return "none"
    if column.endswith(("_key", "_code", "_id", "year", "month", "day", "quarter", "week")):
        return "none"
    return "sum"


def _is_hidden(name: str, column: str) -> bool:
    """Surrogate keys are machinery. A report author should never see them in the field list."""
    return column.endswith("_key") or (name == MEASURE_TABLE and column == "placeholder")


def _reference(table: str, column: str) -> str:
    """A column reference for a relationship, quoted only where TMDL requires it."""
    presented = column_name(column)
    quoted = presented if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", presented) else f"'{presented}'"
    return f"{table}.{quoted}"


def measure_dax(name: str, metric: semantic.Metric) -> str:
    """One measure's DAX, generated from the metric definition.

    A base metric is one filtered aggregation over ``fact_metric`` — the filter names the metric,
    which is the measure's own identity, and nothing about which accounts it comprises. That
    mapping lives in the star.

    A derived metric is its derivation, unchanged. ``[Gross Revenue] - [Contra Revenue]`` is
    already valid DAX, which is why the expression language was given that syntax.
    """
    if metric.derivation:
        return expressions.to_dax(metric.derivation)
    value = column_name("value")
    metric_column = column_name("name")
    return f'CALCULATE(SUM(fact_metric[{value}]), dim_metric[{metric_column}] = "{name}")'


def _measures_table() -> str:
    """The single measures table. A measures-only table still needs a column to exist.

    TMDL parses a table with a partition and no columns; Power BI rejects it on load. The
    placeholder is hidden, so a report author never sees it.
    """
    # A /// line describes the object that *follows* it; it is not a free-standing comment.
    # A blank line between the two leaves it describing nothing, and Microsoft's own TMDL
    # parser rejects the file with "Unexpected line type: Empty!". The convention belongs to
    # the table it governs, immediately above the declaration.
    lines = [
        VARIANCE_HEADER,
        f"table {MEASURE_TABLE}",
        f"\tlineageTag: table-{MEASURE_TABLE.lower()}",
        "\tcolumn 'placeholder'",
        "\t\tdataType: string",
        "\t\tisHidden",
        "\t\tsummarizeBy: none",
        "\t\tsourceColumn: placeholder",
        f"\t\tlineageTag: {MEASURE_TABLE}-placeholder",
        "",
    ]
    for name, metric in semantic.ALL_METRICS.items():
        lines.append(f"\t/// {metric.description}")
        lines.append(f"\tmeasure '{name}' = {measure_dax(name, metric)}")
        lines.append(f"\t\tformatString: {metric.format_string}")
        lines.append(f"\t\tdisplayFolder: {metric.display_folder}")
        lines.append(f"\t\tlineageTag: metric-{name.lower().replace(' ', '-').replace('%', 'pct')}")
        lines.append("")

    # Budget exists only under Balanced Base. A blank visual reads as a rendering failure and a
    # blank inside a variance silently becomes the full value of the other side — criterion 5.25.
    lines += [
        "\t/// States that a version and scenario pairing was never approved, rather than",
        "\t/// rendering blank. Budget exists under Balanced Base only.",
        "\tmeasure 'Selection Status' = "
        'IF(ISBLANK([Net Revenue]), "not applicable - this version and scenario '
        'combination was never approved", "")',
        "\t\tdisplayFolder: Model",
        "\t\tlineageTag: metric-selection-status",
        "",
        f"\tpartition {MEASURE_TABLE} = m",
        "\t\tmode: import",
        "\t\tsource = let Source = #table(type table [placeholder = text], {}) in Source",
        "",
    ]
    return "\n".join(lines)


def _table_tmdl(name: str, frame) -> str:
    """One table. Properties before children — the rule Power BI rejected the project over.

    TMDL closes an object's property list as soon as its first child object opens, so a
    table-level property emitted after the columns is a parse error, not a style problem. The
    original generator wrote ``dataCategory`` at the end and Desktop refused the file at that
    exact line.
    """
    lines = [f"table {name}"]

    # --- table-level properties, all of them, before any child object --------------------
    if name == "dim_date":
        # Marks this as the date table. Without it Power BI falls back to auto date/time, which
        # would put time intelligence outside the semantic layer's control.
        lines.append("\tdataCategory: Time")
    lines.append(f"\tlineageTag: table-{name}")
    lines.append("")

    # --- children ------------------------------------------------------------------------
    for physical in frame.columns:
        series = frame[physical]
        presented = column_name(physical)
        lines.append(f"\tcolumn '{presented}'")
        lines.append(f"\t\tdataType: {_data_type(series)}")
        if name == "dim_date" and physical == "date":
            # The date table's key column. "Mark as date table" needs a unique, contiguous
            # date column, and this is how that column is identified.
            lines.append("\t\tisKey")
        if _is_hidden(name, physical):
            lines.append("\t\tisHidden")
        lines.append(f"\t\tsummarizeBy: {_summarize_by(physical, series)}")
        lines.append(f"\t\tsourceColumn: {physical}")
        lines.append(f"\t\tlineageTag: {name}-{physical}")
        lines.append("")

    lines.append(f"\tpartition {name} = m")
    lines.append("\t\tmode: import")
    lines.append(
        "\t\tsource = let Source = Parquet.Document(File.Contents("
        f'Text.Combine({{ProjectRoot, "{RELATIVE_STAR}/{name}.parquet"}}))) in Source'
    )
    lines.append("")
    return "\n".join(lines)


def _model_tmdl() -> str:
    lines = [
        "model Model",
        "\tculture: en-GB",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "",
        "\tannotation __PBI_TimeIntelligenceEnabled = 0",
        "",
    ]
    for name in (MEASURE_TABLE, *MODEL_TABLES):
        lines.append(f"ref table {name}")
    lines.append("")
    return "\n".join(lines)


def _expressions_tmdl() -> str:
    """The one shared M expression, in its own file because that is where expressions live.

    ``ProjectRoot`` is a parameter rather than a baked path: an absolute path in a committed
    file would name the machine that generated it, and Power Query cannot resolve a relative
    one. It defaults to empty, so the model opens and reports a data-source error until it is
    set once — see ``powerbi/README.md``.
    """
    return "\n".join(
        [
            'expression ProjectRoot = "" meta [IsParameterQuery=true, Type="Text", '
            "IsParameterQueryRequired=true]",
            "\tlineageTag: expression-project-root",
            "",
        ]
    )


def _relationships_tmdl() -> str:
    lines = []
    for from_table, from_column, to_table, to_column in RELATIONSHIPS:
        name = f"{from_table}-{from_column}-{to_table}"
        lines += [
            f"relationship {name}",
            "\tfromCardinality: many",
            "\ttoCardinality: one",
            # Single direction everywhere. Bi-directional filtering introduces ambiguity that
            # `.claude/rules/powerbi-pbip.md` requires an ADR to accept, and none is warranted.
            "\tcrossFilteringBehavior: oneDirection",
            f"\tfromColumn: {_reference(from_table, from_column)}",
            f"\ttoColumn: {_reference(to_table, to_column)}",
            "",
        ]
    return "\n".join(lines)


#: Page geometry. A report definition needs real numbers here; Desktop lays out against them.
PAGE_WIDTH = 1280.0
PAGE_HEIGHT = 720.0
DISCLOSURE_TEXT = "Northlake, Inc. is an illustrative company. All data is synthetic."


def _visual_container(order: int, measure: str, page: str) -> dict:
    """One card visual bound to a measure.

    ``config`` is a **stringified** JSON document inside the report JSON. That is the report
    format's own convention, not a mistake: Desktop stores each visual's configuration as an
    escaped string, and emitting it as a nested object produces a file that parses as JSON and
    is rejected as a report.
    """
    identifier = f"{page}-{order}"
    config = {
        "name": identifier,
        "layouts": [
            {
                "id": 0,
                "position": {
                    "x": 40.0 + (order % 3) * 400.0,
                    "y": 120.0 + (order // 3) * 220.0,
                    "z": float(order),
                    "width": 360.0,
                    "height": 180.0,
                },
            }
        ],
        "singleVisual": {
            "visualType": "card",
            "projections": {"Values": [{"queryRef": f"{MEASURE_TABLE}.{measure}"}]},
            "drillFilterOtherVisuals": True,
            "vcObjects": {
                "title": [
                    {
                        "properties": {
                            "text": {"expr": {"Literal": {"Value": f"'{measure}'"}}},
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                        }
                    }
                ]
            },
        },
    }
    return {
        "x": config["layouts"][0]["position"]["x"],
        "y": config["layouts"][0]["position"]["y"],
        "z": config["layouts"][0]["position"]["z"],
        "width": config["layouts"][0]["position"]["width"],
        "height": config["layouts"][0]["position"]["height"],
        "config": json.dumps(config),
    }


def _disclosure_container(page: str) -> dict:
    """The synthetic-data note, as a real textbox on every page — criterion 5.28."""
    config = {
        "name": f"{page}-disclosure",
        "layouts": [
            {
                "id": 0,
                "position": {"x": 40.0, "y": 660.0, "z": 99.0, "width": 900.0, "height": 32.0},
            }
        ],
        "singleVisual": {
            "visualType": "textbox",
            "objects": {
                "general": [
                    {
                        "properties": {
                            "paragraphs": [
                                {
                                    "textRuns": [
                                        {"value": DISCLOSURE_TEXT, "textStyle": {"fontSize": "9pt"}}
                                    ]
                                }
                            ]
                        }
                    }
                ]
            },
            "drillFilterOtherVisuals": False,
        },
    }
    return {
        "x": 40.0,
        "y": 660.0,
        "z": 99.0,
        "width": 900.0,
        "height": 32.0,
        "config": json.dumps(config),
    }


def _section(order: int, name: str, subtitle: str, measures: tuple[str, ...], drill: bool) -> dict:
    identifier = name.lower().replace(" ", "-").replace("&", "and")
    containers = [
        _visual_container(index, measure, identifier) for index, measure in enumerate(measures)
    ]
    containers.append(_disclosure_container(identifier))
    section_config: dict = {"visibility": 0}
    if drill:
        # A drillthrough target declares the field a visual drills on. Without it the page is
        # an ordinary page and every "drill to detail" in the report goes nowhere.
        section_config["objects"] = {
            "dropShadow": [],
        }
        section_config["type"] = "drillthrough"
    return {
        "name": f"ReportSection{order}",
        "displayName": name,
        "description": subtitle,
        "filters": "[]",
        "ordinal": order,
        "visualContainers": containers,
        "config": json.dumps(section_config),
        "displayOption": 1,
        "width": PAGE_WIDTH,
        "height": PAGE_HEIGHT,
    }


def _report_json() -> str:
    """The report definition, in Power BI's own report format.

    An earlier version of this function emitted a readable schema of this project's own
    invention — pages with a list of measure names. It was valid JSON, it passed every test
    written against it, and Power BI would have rejected it, because a report definition is not
    whatever shape is convenient to assert on.
    """
    sections = [
        _section(order, name, subtitle, measures, drill=False)
        for order, (name, subtitle, measures) in enumerate(PAGES)
    ]
    sections.append(
        _section(
            len(PAGES),
            "Transaction detail",
            "Drillthrough target - GL postings behind any summary figure",
            (),
            drill=True,
        )
    )
    report = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json",
        "config": json.dumps(
            {
                "version": "5.43",
                "activeSectionIndex": 0,
                "defaultDrillFilterOtherVisuals": True,
                "settings": {"useStylableVisualContainerHeader": True},
            }
        ),
        "layoutOptimization": 0,
        "pods": [],
        "resourcePackages": [],
        "sections": sections,
    }
    return json.dumps(report, indent=2) + "\n"


def build(star: dict[str, pd.DataFrame], out_dir: pathlib.Path) -> dict:
    """Write the PBIP project. Returns a summary for the build log."""
    model_dir = out_dir / f"{PROJECT}.SemanticModel" / "definition"
    tables_dir = model_dir / "tables"
    report_dir = out_dir / f"{PROJECT}.Report"
    for directory in (tables_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)

    written = []
    for name in MODEL_TABLES:
        if name not in star:
            continue
        (tables_dir / f"{name}.tmdl").write_text(
            _table_tmdl(name, star[name]), encoding="utf-8", newline="\n"
        )
        written.append(name)

    (tables_dir / f"{MEASURE_TABLE}.tmdl").write_text(
        _measures_table(), encoding="utf-8", newline="\n"
    )
    (model_dir / "model.tmdl").write_text(_model_tmdl(), encoding="utf-8", newline="\n")
    (model_dir / "expressions.tmdl").write_text(_expressions_tmdl(), encoding="utf-8", newline="\n")
    (model_dir / "relationships.tmdl").write_text(
        _relationships_tmdl(), encoding="utf-8", newline="\n"
    )
    (model_dir / "database.tmdl").write_text(
        f"database {PROJECT}\n\tcompatibilityLevel: 1567\n", encoding="utf-8", newline="\n"
    )
    (out_dir / f"{PROJECT}.SemanticModel" / "definition.pbism").write_text(
        json.dumps({"version": "4.0", "settings": {}}, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (report_dir / "report.json").write_text(_report_json(), encoding="utf-8", newline="\n")
    (report_dir / "definition.pbir").write_text(
        json.dumps(
            {
                "$schema": (
                    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
                    "definition/definitionProperties/1.0.0/schema.json"
                ),
                "version": "4.0",
                "datasetReference": {"byPath": {"path": f"../{PROJECT}.SemanticModel"}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (out_dir / f"{PROJECT}.pbip").write_text(
        json.dumps(
            {
                "version": "1.0",
                "artifacts": [{"report": {"path": f"{PROJECT}.Report"}}],
                "settings": {"enableAutoRecovery": False},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    return {
        "tables": written,
        "measures": len(semantic.ALL_METRICS) + 1,
        "relationships": len(RELATIONSHIPS),
        "pages": len(PAGES) + 1,
    }
