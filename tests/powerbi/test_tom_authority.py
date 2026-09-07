"""Microsoft's own TMDL parser, as the external authority — criterion 5.33.

ADR 0022's fourth countermeasure: one external-authority gate per generated artifact, manual only
where the authority cannot be automated. For the semantic model it can be. The Tabular Object
Model ships with DAX Studio and Tabular Editor, and it contains the same deserializer Power BI
Desktop uses.

Skipped rather than failed where no such tool is installed, because a missing local tool is not a
defect in the model. It runs wherever it can, which on this project's development machine is
every commit.

It found a defect on its first run that the project's own validator had passed — a `///`
description followed by a blank line, which describes nothing and which Microsoft's parser
rejects. That is the whole argument for the countermeasure, demonstrated by the countermeasure.
"""

from __future__ import annotations

import pytest

from bellwether.data import generate
from bellwether.paths import POWERBI_DIR
from bellwether.powerbi import tmdl, tom
from bellwether.transform import semantic, star

pytestmark = pytest.mark.requires_tom


@pytest.fixture(scope="module")
def parsed(tmp_path_factory) -> dict:
    if not tom.available():
        pytest.skip("no Tabular Object Model assembly on this machine; see src/.../tom.py")
    out = tmp_path_factory.mktemp("tom")
    tmdl.build(star.build_star(generate.generate()), out)
    result = tom.parse_model(out / f"{tmdl.PROJECT}.SemanticModel" / "definition")
    assert result["ok"], result.get("error")
    return result


def test_the_generated_model_parses(parsed) -> None:
    """The gate itself. Everything below is what the authority can tell us once it opens."""
    assert parsed["ok"]
    assert {t["name"] for t in parsed["tables"]} >= {
        tmdl.MEASURE_TABLE,
        "fact_metric",
        "dim_date",
    }


def test_the_committed_model_parses() -> None:
    """The project in the repository, not only one a test just generated."""
    if not tom.available():
        pytest.skip("no Tabular Object Model assembly on this machine")
    definition = POWERBI_DIR / f"{tmdl.PROJECT}.SemanticModel" / "definition"
    if not definition.exists():
        pytest.skip("run `python -m bellwether.build` first")
    result = tom.parse_model(definition)
    assert result["ok"], result.get("error")


def test_every_metric_arrives_as_a_measure(parsed) -> None:
    """5.11, verified by the parser rather than by reading our own output back."""
    measures = {
        m["name"]
        for t in parsed["tables"]
        if t["name"] == tmdl.MEASURE_TABLE
        for m in t["measures"]
    }
    assert measures - {"Selection Status"} == set(semantic.ALL_METRICS)


def test_measures_keep_their_format_and_folder(parsed) -> None:
    """5.22 and 5.19 — as the model sees them, not as the file spells them."""
    table = next(t for t in parsed["tables"] if t["name"] == tmdl.MEASURE_TABLE)
    by_name = {m["name"]: m for m in table["measures"]}
    for name, metric in semantic.ALL_METRICS.items():
        assert by_name[name]["formatString"] == metric.format_string, name
        assert by_name[name]["displayFolder"] == metric.display_folder, name


def test_no_other_table_carries_a_measure(parsed) -> None:
    """5.19 — one measures table."""
    for table in parsed["tables"]:
        if table["name"] == tmdl.MEASURE_TABLE:
            continue
        assert not table["measures"], table["name"]


def test_the_date_table_is_marked_and_keyed(parsed) -> None:
    """5.18 — Power BI's own reading of it, which is the one that counts."""
    dates = next(t for t in parsed["tables"] if t["name"] == "dim_date")
    assert dates["dataCategory"] == "Time"
    keys = [c["name"] for c in dates["columns"] if c["isKey"]]
    assert keys == ["Date"], keys
    date_column = next(c for c in dates["columns"] if c["name"] == "Date")
    assert date_column["dataType"] == "DateTime"


def test_every_relationship_is_single_direction_and_many_to_one(parsed) -> None:
    """5.20 — bi-directional filtering would need an ADR, and none is warranted."""
    assert len(parsed["relationships"]) == len(tmdl.RELATIONSHIPS)
    for relationship in parsed["relationships"]:
        assert relationship["crossFiltering"] == "OneDirection", relationship
        assert relationship["fromCardinality"] == "Many", relationship
        assert relationship["toCardinality"] == "One", relationship


def test_no_relationship_dangles(parsed) -> None:
    """A relationship naming a column that does not exist fails to resolve, silently."""
    columns = {f"{t['name']}[{c['name']}]" for t in parsed["tables"] for c in t["columns"]}
    for relationship in parsed["relationships"]:
        assert relationship["from"] in columns, relationship["from"]
        assert relationship["to"] in columns, relationship["to"]


def test_every_table_has_a_partition_and_a_column(parsed) -> None:
    """The Measures table shipped without a column: parses as text, rejected as a model."""
    for table in parsed["tables"]:
        assert table["columns"], f"{table['name']} has no columns"
        assert len(table["partitions"]) == 1, table["name"]


def test_surrogate_keys_are_hidden(parsed) -> None:
    hidden = {
        f"{t['name']}[{c['name']}]" for t in parsed["tables"] for c in t["columns"] if c["isHidden"]
    }
    assert "dim_date[Date key]" in hidden
    assert f"{tmdl.MEASURE_TABLE}[placeholder]" in hidden


def test_nothing_that_is_not_a_number_is_summarised(parsed) -> None:
    """ "Sum of Is promotional" is a figure with no meaning that ends up on a slide."""
    for table in parsed["tables"]:
        for column in table["columns"]:
            if column["dataType"] in {"String", "Boolean", "DateTime"}:
                assert column["summarizeBy"] == "None", f"{table['name']}[{column['name']}]"


# --- 5.36: Desktop's own name rule, which TOM does not apply ---------------------------------


@pytest.fixture(scope="module")
def names(tmp_path_factory) -> dict:
    if not tom.names_available():
        pytest.skip("Power BI Desktop's Modeler assembly is not on this machine")
    out = tmp_path_factory.mktemp("names")
    tmdl.build(star.build_star(generate.generate()), out)
    return tom.validate_names(out / f"{tmdl.PROJECT}.SemanticModel" / "definition")


def test_every_object_name_survives_desktops_validator(names) -> None:
    """5.36 — the gate TOM does not provide.

    TOM parsed the model and Desktop refused it: `Unsupported Table name "Measures"`. Parsing is
    a weaker check than it looks, because Desktop applies rules on top of the metadata format.

    The rule is not a reserved-word list, which is why it could not have been guessed. Read out
    of `ModelSchemaValidator.EnsureValidObjectName`, it is exactly:

        name != NameValidator.RemoveInvalidNameCharacters(name, objectType)  ->  reject

    `Measures` sanitises to `Measures 1`, so it fails. Every other name in the model passed, and
    the placeholder column and partition — the suspected cause — were never the problem.
    """
    assert names["ok"], names.get("offenders") or names.get("error")


def test_the_reserved_name_is_reachable_and_still_reserved() -> None:
    """The negative control: the gate must reject the name that broke it.

    Without this, `validate_names` returning ok proves nothing — it would also return ok if the
    reflection silently failed and it checked nothing at all.
    """
    if not tom.names_available():
        pytest.skip("Power BI Desktop's Modeler assembly is not on this machine")
    assert tmdl.MEASURE_TABLE != "Measures"
    assert tmdl.MEASURE_TABLE == "Key Figures"
