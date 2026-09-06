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
    """Never let Power BI implicitly sum a key. An implicit measure is an invented one."""
    if column.endswith(("_key", "_code", "_name")) or _data_type(series) == "string":
        return "none"
    return "none" if column.endswith(("year", "month", "date")) else "sum"


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
    lines = [f"table {MEASURE_TABLE}", "", f"\t{VARIANCE_HEADER}", ""]
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
        "\t\tformatString: 0",
        "\t\tdisplayFolder: Model",
        "\t\tlineageTag: metric-selection-status",
        "",
        "\tpartition Measures = m",
        "\t\tmode: import",
        '\t\tsource = let Source = #table({"placeholder"}, {}) in Source',
        "",
    ]
    return "\n".join(lines)


def _table_tmdl(name: str, frame) -> str:
    lines = [f"table {name}", ""]
    for physical in frame.columns:
        series = frame[physical]
        presented = column_name(physical)
        lines.append(f"\tcolumn '{presented}'")
        lines.append(f"\t\tdataType: {_data_type(series)}")
        lines.append(f"\t\tsummarizeBy: {_summarize_by(physical, series)}")
        lines.append(f"\t\tsourceColumn: {physical}")
        lines.append(f"\t\tlineageTag: {name}-{physical}")
        lines.append("")
    if name == "dim_date":
        # A dedicated date table, marked as such. Auto date/time is disabled at the model level;
        # relying on it would put time intelligence outside the semantic layer's control.
        lines.append("\tdataCategory: Time")
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
        '\texpression ProjectRoot = "../../../" meta [IsParameterQuery=true, Type="Text"]',
        "",
    ]
    for name in (MEASURE_TABLE, *MODEL_TABLES):
        lines.append(f"ref table {name}")
    lines.append("")
    return "\n".join(lines)


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
            f"\tfromColumn: {from_table}.'{column_name(from_column)}'",
            f"\ttoColumn: {to_table}.'{column_name(to_column)}'",
            "",
        ]
    return "\n".join(lines)


def _report_json() -> str:
    pages = []
    for order, (name, subtitle, measures) in enumerate(PAGES):
        pages.append(
            {
                "name": name.lower().replace(" ", "-"),
                "displayName": name,
                "ordinal": order,
                "subtitle": subtitle,
                "visuals": [
                    {
                        "name": f"{name.lower().replace(' ', '-')}-{measure.lower()}",
                        "measure": measure,
                        "drillthrough": "Transaction detail",
                    }
                    for measure in measures
                ],
                "disclosure": (
                    "Northlake, Inc. is an illustrative company. All data is synthetic."
                ),
            }
        )
    pages.append(
        {
            "name": "transaction-detail",
            "displayName": "Transaction detail",
            "ordinal": len(PAGES),
            "subtitle": "Drillthrough target — GL postings behind any summary figure",
            "isDrillthroughTarget": True,
            "visuals": [{"name": "gl-detail", "table": "fact_gl", "drillthrough": None}],
            "disclosure": "Northlake, Inc. is an illustrative company. All data is synthetic.",
        }
    )
    return json.dumps({"version": "1.0", "pages": pages}, indent=2) + "\n"


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
