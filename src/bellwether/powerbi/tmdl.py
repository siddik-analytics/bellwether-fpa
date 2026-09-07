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

import hashlib
import json
import pathlib
import re

import pandas as pd

from bellwether.transform import expressions, semantic

PROJECT = "northlake"
#: NOT "Measures". Power BI Desktop rejects that name outright: its own NameValidator sanitises
#: it to "Measures 1", and ModelSchemaValidator rejects any object whose name differs from its
#: sanitised form. "Key Figures" is Desktop's own term for this table and passes the same check.
MEASURE_TABLE = "Key Figures"

#: Where the star lives, relative to the repository root. An absolute path would embed the
#: machine that generated the project into a committed text file, breaking both portability and
#: the byte-for-byte regeneration criterion 5.29 asserts.
RELATIVE_STAR = "data/star"

#: Every `$schema` Power BI Desktop writes, taken from its own output rather than from
#: documentation or a guess. The fixture is `tests/fixtures/powerbi-desktop-blank/` and
#: `tests/powerbi/test_schema_fixture.py` asserts each value below against it — because the five
#: values these replaced were all transcribed, and all five were wrong.
SCHEMA_BASE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
SCHEMAS: dict[str, str] = {
    "report": f"{SCHEMA_BASE}/report/3.3.0/schema.json",
    "pagesMetadata": f"{SCHEMA_BASE}/pagesMetadata/1.1.0/schema.json",
    "page": f"{SCHEMA_BASE}/page/2.1.0/schema.json",
    "versionMetadata": f"{SCHEMA_BASE}/versionMetadata/1.0.0/schema.json",
}

#: The visual container schema, and the fact that a visual carries exactly these keys. From
#: `tests/fixtures/powerbi-desktop-visuals/`, where all 24 of Desktop's own visuals share one
#: shape: `$schema`, `name`, `position`, `visual`.
VISUAL_SCHEMA = f"{SCHEMA_BASE}/visualContainer/2.12.0/schema.json"

#: `cardVisual`, not `card`. The reference lists both the modern name and 23 others; guessing
#: the older one would have produced a visual Power BI does not recognise.
CARD_VISUAL = "cardVisual"

#: Files Desktop writes with **no** `$schema`. Adding one would be inventing a contract, which
#: is what the previous generator did to two of these three.
WITHOUT_SCHEMA: tuple[str, ...] = ("northlake.pbip", "definition.pbir", "definition.pbism")

#: Desktop's own values. `compatibilityLevel` was 1567 and the database was named; both wrong.
PBISM_VERSION = "4.2"
PBIR_VERSION = "4.0"
REPORT_DEFINITION_VERSION = "2.0.0"
COMPATIBILITY_LEVEL = 1606

#: Desktop writes the database unnamed. The generator named it, which TMDL tolerates and
#: Desktop does not produce.
DATABASE_TMDL = f"database\n\tcompatibilityLevel: {COMPATIBILITY_LEVEL}\n"

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


def lineage_tag(name: str) -> str:
    """A lineage tag for a table. Slugged, because a tag with a space in it reads as two."""
    return "table-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def tmdl_name(name: str) -> str:
    """A TMDL object name, quoted only when it must be.

    An identifier containing anything but letters, digits and underscores has to be quoted in a
    declaration. `ref table Key Figures` parses as a name followed by a stray token; the
    authority reported exactly that, at the line, the moment the table was renamed.
    """
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else f"'{name}'"


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

#: The drillthrough target. Not one of the four the rules file fixes.
DRILLTHROUGH_PAGE = "Transaction detail"

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
        f"table {tmdl_name(MEASURE_TABLE)}",
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
        f"\tpartition {tmdl_name(MEASURE_TABLE)} = m",
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

    lines.append(f"\tpartition {tmdl_name(name)} = m")
    lines.append("\t\tmode: import")
    lines.append(
        "\t\tsource = let Source = Parquet.Document(File.Contents("
        f'Text.Combine({{ProjectRoot, "{RELATIVE_STAR}/{name}.parquet"}}))) in Source'
    )
    lines.append("")
    return "\n".join(lines)


def _model_tmdl() -> str:
    lines = [
        # The synthetic-data note. It cannot go on a report page without an authoritative
        # example of a visual, so it lives where the model carries it and every consumer of the
        # model sees it - CLAUDE.md rule 6 requires every generated artifact to say this.
        f"/// {DISCLOSURE_TEXT}",
        "model Model",
        "\tculture: en-GB",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "",
        "\tannotation __PBI_TimeIntelligenceEnabled = 0",
        "",
    ]
    for name in (MEASURE_TABLE, *MODEL_TABLES):
        lines.append(f"ref table {tmdl_name(name)}")
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


#: Desktop's own page geometry for a new report.
PAGE_WIDTH = 1920
PAGE_HEIGHT = 1080
DISCLOSURE_TEXT = "Northlake, Inc. is an illustrative company. All data is synthetic."


def page_name(display_name: str) -> str:
    """A stable folder name for a page.

    Desktop uses an opaque twenty-character id. A readable slug is equally valid and this
    repository is meant to be read, so the folder says which page it is. It must be
    deterministic either way, or regeneration stops being byte-identical.
    """
    return display_name.lower().replace("&", "and").replace(" ", "-")


def visual_name(page: str, measure: str) -> str:
    """A stable twenty-character id, in Desktop's own shape.

    Desktop uses twenty lowercase hex characters. A hash of the page and measure gives the same
    shape deterministically, which byte-identical regeneration requires and a random id would
    break on every build.
    """
    digest = hashlib.sha256(f"{page}|{measure}".encode()).hexdigest()
    return digest[:20]


def _visual_json(page: str, measure: str, order: int) -> str:
    """One visual container, in the shape the reference proves.

    **The measure is not bound.** Every visual in the reference is an unbound placeholder, so
    this project has no authoritative example of a field binding — the `visual.query` shape is
    still unknown. Emitting a guess is the defect ADR 0022 exists to prevent, so the container is
    real and correct and the binding is absent. Criterion 5.27 stays open until a reference with
    a bound field exists.
    """
    return (
        json.dumps(
            {
                "$schema": VISUAL_SCHEMA,
                "name": visual_name(page, measure),
                "position": {
                    "x": 40 + (order % 3) * 620,
                    "y": 120 + (order // 3) * 300,
                    "z": order,
                    "height": 280,
                    "width": 560,
                    "tabOrder": order,
                },
                "visual": {"visualType": CARD_VISUAL, "drillFilterOtherVisuals": True},
            },
            indent=2,
        )
        + "\n"
    )


def _page_json(display_name: str) -> str:
    return (
        json.dumps(
            {
                "$schema": SCHEMAS["page"],
                "name": page_name(display_name),
                "displayName": display_name,
                "displayOption": "FitToPage",
                "height": PAGE_HEIGHT,
                "width": PAGE_WIDTH,
            },
            indent=2,
        )
        + "\n"
    )


def _pages_json(display_names: list[str]) -> str:
    return (
        json.dumps(
            {
                "$schema": SCHEMAS["pagesMetadata"],
                "pageOrder": [page_name(name) for name in display_names],
                "activePageName": page_name(display_names[0]),
            },
            indent=2,
        )
        + "\n"
    )


def _report_json() -> str:
    """The report definition.

    Two generations of this function were wrong in different ways. The first invented a schema
    of this project's own design — pages holding measure names — which every test written
    against it accepted. The second used Power BI's *legacy* report format, a single
    `report.json` of `sections` and `visualContainers` at the report root. Desktop writes
    neither: it writes PBIR, where `definition/report.json` holds report-level settings and each
    page is its own file under `definition/pages/`.

    Both mistakes came from the same place. Nobody had looked at what Desktop actually produces.
    """
    return (
        json.dumps(
            {
                "$schema": SCHEMAS["report"],
                # Desktop's own settings block, copied from the reference rather than
                # chosen. The theme collection and resource packages are deliberately omitted:
                # they point at a 99 KB stock theme file this repository does not ship.
                "settings": {
                    "useStylableVisualContainerHeader": True,
                    "exportDataMode": "AllowSummarized",
                    "defaultDrillFilterOtherVisuals": True,
                    "allowChangeFilterTypes": True,
                    "useEnhancedTooltips": True,
                    "useDefaultAggregateDisplayName": True,
                },
            },
            indent=2,
        )
        + "\n"
    )


def _version_json() -> str:
    return (
        json.dumps(
            {"$schema": SCHEMAS["versionMetadata"], "version": REPORT_DEFINITION_VERSION},
            indent=2,
        )
        + "\n"
    )


def _write_report(report_dir: pathlib.Path) -> list[str]:
    """Write the PBIR report: settings, version, page order, and one file per page.

    Visual containers are generated from the shape a second Desktop reference proves
    (`tests/fixtures/powerbi-desktop-visuals/`). Their **field bindings are not**: every visual
    in that reference is an unbound placeholder, so the `visual.query` shape remains unknown and
    a guess would be the defect ADR 0022 exists to prevent.
    """
    definition = report_dir / "definition"
    pages_dir = definition / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    display_names = [name for name, _, _ in PAGES] + [DRILLTHROUGH_PAGE]
    (definition / "report.json").write_text(_report_json(), encoding="utf-8", newline="\n")
    (definition / "version.json").write_text(_version_json(), encoding="utf-8", newline="\n")
    (pages_dir / "pages.json").write_text(
        _pages_json(display_names), encoding="utf-8", newline="\n"
    )
    measures_for = {name: measures for name, _, measures in PAGES}
    for display_name in display_names:
        slug = page_name(display_name)
        page_dir = pages_dir / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "page.json").write_text(
            _page_json(display_name), encoding="utf-8", newline="\n"
        )
        for order, measure in enumerate(measures_for.get(display_name, ())):
            visual_dir = page_dir / "visuals" / visual_name(slug, measure)
            visual_dir.mkdir(parents=True, exist_ok=True)
            (visual_dir / "visual.json").write_text(
                _visual_json(slug, measure, order), encoding="utf-8", newline="\n"
            )
    return display_names


def build(star: dict[str, pd.DataFrame], out_dir: pathlib.Path) -> dict:
    """Write the PBIP project. Returns a summary for the build log."""
    model_dir = out_dir / f"{PROJECT}.SemanticModel" / "definition"
    tables_dir = model_dir / "tables"
    report_dir = out_dir / f"{PROJECT}.Report"
    for directory in (tables_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)

    # Remove tables from a previous run before writing. Without this a renamed table leaves its
    # old file behind and the model quietly contains both - which is how the rejected "Measures"
    # table survived its own rename and kept failing the name gate.
    for stale in tables_dir.glob("*.tmdl"):
        stale.unlink()

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
    (model_dir / "database.tmdl").write_text(DATABASE_TMDL, encoding="utf-8", newline="\n")
    (out_dir / f"{PROJECT}.SemanticModel" / "definition.pbism").write_text(
        json.dumps({"version": PBISM_VERSION, "settings": {}}, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    pages = _write_report(report_dir)
    (report_dir / "definition.pbir").write_text(
        json.dumps(
            # No $schema: Desktop writes none here, and adding one invents a contract.
            {
                "version": PBIR_VERSION,
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
                "settings": {"enableAutoRecovery": True},
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
        "pages": len(pages),
    }
