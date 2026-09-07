"""Power BI is a thin consumer — criteria 5.10 to 5.29.

The guarantee here is **weaker than the Excel reconciliation and is stated as weaker.** There is
no supported way to evaluate a DAX measure from a script, so CI cannot prove the measures compute
correctly. What it can prove, and does, is that every measure was *generated* from a `Metric` in
the semantic layer — which makes redefinition structurally impossible rather than merely
discouraged. The numeric reconciliation is `requires_powerbi`, local, and never claimed as CI.
"""

from __future__ import annotations

import json
import re

import pytest

from bellwether.data import generate
from bellwether.paths import POWERBI_DIR
from bellwether.powerbi import tmdl
from bellwether.transform import semantic, star

MEASURE = re.compile(r"^\tmeasure '([^']+)' = (.+)$", re.M)


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> dict:
    tables = generate.generate()
    schema = star.build_star(tables)
    out = tmp_path_factory.mktemp("pbip")
    summary = tmdl.build(schema, out)
    return {"dir": out, "summary": summary, "star": schema}


def _measures(directory) -> dict[str, str]:
    path = (
        directory
        / f"{tmdl.PROJECT}.SemanticModel"
        / "definition"
        / "tables"
        / f"{tmdl.MEASURE_TABLE}.tmdl"
    )
    return dict(MEASURE.findall(path.read_text(encoding="utf-8")))


def _all_tmdl(directory) -> str:
    definition = directory / f"{tmdl.PROJECT}.SemanticModel" / "definition"
    return "\n".join(p.read_text(encoding="utf-8") for p in definition.rglob("*.tmdl"))


# --- 5.10, 5.11, 5.13 generated, not authored -------------------------------------------------


def test_every_measure_is_generated_from_a_metric(built) -> None:
    """5.10 — regenerating reproduces the committed file exactly.

    This is the whole verification strategy: a measure edited in the tool fails the build,
    because the build would overwrite it and the diff would not be empty.
    """
    measures = _measures(built["dir"])
    for name, dax in measures.items():
        if name == "Selection Status":
            continue
        metric = semantic.ALL_METRICS[name]
        assert dax == tmdl.measure_dax(name, metric), name


def test_regeneration_is_byte_identical(built, tmp_path) -> None:
    """5.29 — a hand-edited measure fails the build."""
    again = tmp_path / "again"
    tmdl.build(built["star"], again)
    first = sorted(
        p.relative_to(built["dir"]).as_posix() for p in built["dir"].rglob("*") if p.is_file()
    )
    second = sorted(p.relative_to(again).as_posix() for p in again.rglob("*") if p.is_file())
    assert first == second
    for relative in first:
        assert (built["dir"] / relative).read_bytes() == (again / relative).read_bytes(), relative


def test_the_mapping_to_metrics_is_total_in_both_directions(built) -> None:
    """5.11 and 5.13 — no metric without a measure, no measure without a metric."""
    measures = set(_measures(built["dir"])) - {"Selection Status"}
    assert measures == set(semantic.ALL_METRICS), {
        "only in DAX": sorted(measures - set(semantic.ALL_METRICS)),
        "only in the semantic layer": sorted(set(semantic.ALL_METRICS) - measures),
    }


def test_derived_measures_are_their_derivation_unchanged(built) -> None:
    """The payoff of giving the expression language DAX's own syntax — ADR 0019."""
    measures = _measures(built["dir"])
    assert measures["Net Revenue"] == "[Gross Revenue] - [Contra Revenue]"
    assert measures["Gross Margin %"] == "DIVIDE([Gross Profit], [Net Revenue])"
    for name, metric in semantic.DERIVED.items():
        assert measures[name] == metric.derivation, name


# --- 5.12 and 5.14 no business logic in DAX -----------------------------------------------------


def test_no_dax_expression_carries_business_logic(built) -> None:
    """5.12 — the prohibition, stated so it can fail loudly.

    An account code, an account type, a department or an allocation rule appearing in DAX means
    the definition now exists twice. This is a crude grep and that is exactly right: if a
    reviewer can find an account code in the measures file, the positioning failed.
    """
    tables = generate.generate()
    codes = set(tables["dim_gl_account"]["account_code"].astype(str))
    types = set(tables["dim_gl_account"]["account_type"].dropna().astype(str))
    departments = set(tables["dim_department"]["department_name"].astype(str))

    offenders = []
    for name, dax in _measures(built["dir"]).items():
        for token in codes | types | departments | {"BY_UNITS"}:
            if re.search(rf"\b{re.escape(token)}\b", dax):
                offenders.append(f"{name}: {token} in {dax}")
    assert not offenders, offenders


def test_channel_contribution_needs_no_dax_conditional(built) -> None:
    """5.14 — the allocation is resolved in the star, so DAX only groups.

    Contribution Profit is the same arithmetic as EBITDA; what makes it a channel figure is the
    filter context a report applies, not a rule written into the measure.
    """
    measures = _measures(built["dir"])
    contribution = measures["Contribution Profit"]
    assert contribution == "[Gross Profit] - [Operating Expense]"
    for forbidden in ("IF(", "SWITCH(", "units", "allocat"):
        assert forbidden.lower() not in contribution.lower(), contribution


def test_the_fact_carries_the_resolved_channel(built) -> None:
    """The other half of 5.14: the split arrived as data."""
    fact = built["star"]["fact_metric"]
    assert set(fact["channel_allocation"].unique()) <= {
        "DTC",
        "Wholesale",
        "Unallocated corporate",
    }
    assert "BY_UNITS" not in set(fact["channel_allocation"].unique())


# --- 5.16 to 5.25 model conventions --------------------------------------------------------------


def test_no_binary_artifact_anywhere(built) -> None:
    """5.16 — PBIP text only. A .pbix defeats the point of the repo being reviewable."""
    for directory in (built["dir"], POWERBI_DIR):
        if not directory.exists():
            continue
        offenders = [p.name for p in directory.rglob("*") if p.suffix in {".pbix", ".pbit"}]
        assert not offenders, offenders


def test_version_and_scenario_are_two_dimensions(built) -> None:
    """5.17 — ADR 0007. A single dimension cannot express forecast revision."""
    text = _all_tmdl(built["dir"])
    assert "table dim_version" in text
    assert "table dim_scenario" in text
    assert "dim_version_scenario" not in text
    relationships = (
        built["dir"] / f"{tmdl.PROJECT}.SemanticModel" / "definition" / "relationships.tmdl"
    ).read_text(encoding="utf-8")
    # Unquoted: TMDL only quotes an identifier that needs it, and these do not.
    assert "toColumn: dim_version.Version" in relationships
    assert "toColumn: dim_scenario.Scenario" in relationships
    assert "toColumn: dim_gl_account.'Account code'" in relationships, (
        "a name with a space must be quoted"
    )


def test_the_date_table_is_marked_and_auto_date_time_is_off(built) -> None:
    """5.18 — relying on auto date/time puts time intelligence outside the semantic layer."""
    dates = (
        built["dir"] / f"{tmdl.PROJECT}.SemanticModel" / "definition" / "tables" / "dim_date.tmdl"
    ).read_text(encoding="utf-8")
    assert "dataCategory: Time" in dates
    assert "dataType: dateTime" in dates, "a string date column silently disables time intelligence"

    model = (
        built["dir"] / f"{tmdl.PROJECT}.SemanticModel" / "definition" / "model.tmdl"
    ).read_text(encoding="utf-8")
    assert "__PBI_TimeIntelligenceEnabled = 0" in model
    assert "discourageImplicitMeasures" in model


def test_all_measures_live_in_one_table_with_display_folders(built) -> None:
    """5.19 — measures scattered across fact tables are how a model becomes unnavigable."""
    definition = built["dir"] / f"{tmdl.PROJECT}.SemanticModel" / "definition" / "tables"
    for path in definition.glob("*.tmdl"):
        if path.stem == tmdl.MEASURE_TABLE:
            continue
        assert "\tmeasure " not in path.read_text(encoding="utf-8"), path.name

    measures_text = (definition / f"{tmdl.MEASURE_TABLE}.tmdl").read_text(encoding="utf-8")
    folders = set(re.findall(r"displayFolder: (.+)", measures_text))
    assert folders >= {"P&L", "Channel", "Below the line"}


def test_every_relationship_is_single_direction(built) -> None:
    """5.20 — bi-directional filtering needs an ADR, and none is warranted."""
    relationships = (
        built["dir"] / f"{tmdl.PROJECT}.SemanticModel" / "definition" / "relationships.tmdl"
    ).read_text(encoding="utf-8")
    declared = relationships.count("relationship ")
    assert declared == len(tmdl.RELATIONSHIPS)
    assert relationships.count("crossFilteringBehavior: oneDirection") == declared
    assert "bothDirections" not in relationships


def test_there_are_no_calculated_columns(built) -> None:
    """5.21 — prefer a measure. A calculated column needs a stated reason, and none has one.

    In TMDL a calculated column is a ``column`` declaration carrying an expression. A sourced
    column names a ``sourceColumn`` instead, so the check is precise rather than a search for an
    equals sign, which would also catch annotations and the ProjectRoot parameter.
    """
    offenders = [
        line.strip()
        for line in _all_tmdl(built["dir"]).splitlines()
        if line.strip().startswith("column ") and "=" in line
    ]
    assert not offenders, offenders


def test_format_strings_come_from_the_metric(built) -> None:
    """5.22 — set on the measure, never on a visual."""
    text = (
        built["dir"]
        / f"{tmdl.PROJECT}.SemanticModel"
        / "definition"
        / "tables"
        / f"{tmdl.MEASURE_TABLE}.tmdl"
    ).read_text(encoding="utf-8")
    for name, metric in semantic.ALL_METRICS.items():
        block = text.split(f"measure '{name}' =")[1].split("measure ")[0]
        assert f"formatString: {metric.format_string}" in block, name

    definition = built["dir"] / f"{tmdl.PROJECT}.Report" / "definition"
    report = "\n".join(p.read_text(encoding="utf-8") for p in definition.rglob("*.json"))
    assert "formatString" not in report, "a format string in the report overrides the measure"


def test_the_variance_convention_is_stated_once(built) -> None:
    """5.23 — documented at the top of the measures file, and sourced from the definition."""
    text = (
        built["dir"]
        / f"{tmdl.PROJECT}.SemanticModel"
        / "definition"
        / "tables"
        / f"{tmdl.MEASURE_TABLE}.tmdl"
    ).read_text(encoding="utf-8")
    assert "Favourable variance is positive" in text
    assert text.count("Favourable variance is positive") == 1
    assert "Metric.is_cost" in text


def test_scenarios_are_not_ordered_as_upside_base_downside(built) -> None:
    """5.24 — the natural thing for a report author to do, and it inverts the finding.

    Wholesale Acceleration carries the highest revenue and the worst cash. An ordinal sort column
    or a diverging colour ramp would present it as the upside case.
    """
    text = _all_tmdl(built["dir"])
    scenario_block = text.split("table dim_scenario")[1].split("table ")[0]
    assert "sortByColumn" not in scenario_block, "an ordinal on scenario implies a ranking"

    definition = built["dir"] / f"{tmdl.PROJECT}.Report" / "definition"
    report = "\n".join(p.read_text(encoding="utf-8") for p in definition.rglob("*.json")).lower()
    for banned in ("upside", "downside", "base case", "diverging"):
        assert banned not in report, banned


def test_an_unapproved_combination_states_itself(built) -> None:
    """5.25 — Budget exists under Balanced Base only, and blank reads as zero."""
    measures = _measures(built["dir"])
    assert "Selection Status" in measures
    assert "not applicable" in measures["Selection Status"]

    # And the underlying asymmetry is real, so the measure has something to catch.
    fact = built["star"]["fact_metric"]
    budget = fact[fact["version_name"] == "Budget"]
    assert set(budget["scenario_name"].unique()) == {"Balanced Base"}


# --- 5.26 to 5.28 the report ----------------------------------------------------------------


def _report_dir(directory):
    return directory / f"{tmdl.PROJECT}.Report" / "definition"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_the_report_is_in_power_bis_own_format(built) -> None:
    """Two generations of this were wrong, and neither could be caught from inside.

    The first invented a schema of this project's own design. The second used Power BI's legacy
    report format — a single `report.json` of `sections` and `visualContainers`. Desktop writes
    PBIR: `definition/report.json` for report settings, `definition/version.json`, and a file
    per page under `definition/pages/`. That was settled by looking at Desktop's output, which
    is now the fixture in `tests/fixtures/powerbi-desktop-blank/`.
    """
    definition = _report_dir(built["dir"])
    assert (definition / "report.json").is_file()
    assert (definition / "version.json").is_file()
    assert (definition / "pages" / "pages.json").is_file()
    assert not (built["dir"] / f"{tmdl.PROJECT}.Report" / "report.json").exists(), (
        "the legacy report format is still being written"
    )
    report = _json(definition / "report.json")
    assert "sections" not in report, "sections belong to the legacy format"
    assert isinstance(report["settings"], dict), "PBIR settings are an object, not a string"


def test_four_pages_in_the_order_the_rules_fix(built) -> None:
    """5.26 — plus the drillthrough target, which is not one of the four."""
    pages = _json(_report_dir(built["dir"]) / "pages" / "pages.json")
    expected = [
        tmdl.page_name(name)
        for name in [
            "Executive summary",
            "P&L detail",
            "Cash and working capital",
            "Unit economics",
            tmdl.DRILLTHROUGH_PAGE,
        ]
    ]
    assert pages["pageOrder"] == expected
    assert pages["activePageName"] == expected[0]


def test_every_page_in_the_order_has_a_file(built) -> None:
    """A page listed in pageOrder with no page.json is a report that opens broken."""
    definition = _report_dir(built["dir"])
    pages = _json(definition / "pages" / "pages.json")
    for name in pages["pageOrder"]:
        page = definition / "pages" / name / "page.json"
        assert page.is_file(), name
        assert _json(page)["name"] == name


def test_page_display_names_are_business_language(built) -> None:
    definition = _report_dir(built["dir"])
    names = {_json(path)["displayName"] for path in (definition / "pages").rglob("page.json")}
    assert "Executive summary" in names
    assert tmdl.DRILLTHROUGH_PAGE in names


def test_every_card_is_bound_to_a_measure(built) -> None:
    """5.27 — the cards display something now.

    Bound from `tests/fixtures/powerbi-desktop-bound/`, which is the third Desktop reference and
    the first to contain a field actually assigned to a visual. Before it, the cards were
    correctly shaped and empty, and that was recorded as not met rather than dressed up.
    """
    definition = _report_dir(built["dir"])
    cards = [
        _json(path)
        for path in definition.rglob("visual.json")
        if _json(path)["visual"]["visualType"] == tmdl.CARD_VISUAL
    ]
    assert cards, "no cards were generated"
    known = set(_measures(built["dir"]))
    for card in cards:
        projections = card["visual"]["query"]["queryState"]["Data"]["projections"]
        assert len(projections) == 1, card["name"]
        field = projections[0]["field"]["Measure"]
        assert field["Expression"]["SourceRef"]["Entity"] == tmdl.MEASURE_TABLE
        assert field["Property"] in known, field["Property"]
        assert projections[0]["queryRef"] == f"{tmdl.MEASURE_TABLE}.{field['Property']}"


def test_the_disclosure_is_carried_by_the_model(built) -> None:
    """5.28, as far as it can currently hold.

    The note cannot go on a report page without a visual, so it is the model's own description,
    where every consumer of the model meets it. Verified through the parser in
    `test_tom_authority.py` as well as here.
    """
    model = (
        built["dir"] / f"{tmdl.PROJECT}.SemanticModel" / "definition" / "model.tmdl"
    ).read_text(encoding="utf-8")
    assert model.splitlines()[0].startswith("/// ")
    assert "illustrative company" in model
    assert "synthetic" in model


def test_no_absolute_path_is_committed(built) -> None:
    """A generated project must not embed the machine that generated it."""
    text = _all_tmdl(built["dir"])
    assert "C:/" not in text and "C:\\" not in text
    assert "ProjectRoot" in text


# --- the numeric check, local only ------------------------------------------------


# 5.15 lives in `test_xmla_reconciliation.py` now. The spec called for exporting a table visual
# to CSV; querying Desktop's own Analysis Services instance over XMLA is the same criterion done
# better, because a visual export reads a rendering and a DAX query reads the engine.
