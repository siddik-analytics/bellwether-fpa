"""The TMDL structural validator — criterion 5.31.

This exists because of a specific failure. The project generated cleanly, regenerated
byte-identically, passed every test in `test_generated.py`, and Power BI Desktop refused to open
it:

    Parsing error type - Indentation
    Document - './tables/dim_date'
    Line 75 - '\\tdataCategory: Time'

`dataCategory` is a table property, and TMDL closes an object's property list the moment its
first child object opens. The generator emitted it after the columns. No DAX engine was needed to
find that — it is a grammar error, and a grammar can be checked headless.

So these tests are the ones that would have caught it, and each negative case below is a defect
the generator actually shipped rather than an imagined one.
"""

from __future__ import annotations

import pytest

from bellwether.data import generate
from bellwether.paths import POWERBI_DIR
from bellwether.powerbi import tmdl, validate
from bellwether.transform import star


@pytest.fixture(scope="module")
def model_dir(tmp_path_factory):
    tables = generate.generate()
    out = tmp_path_factory.mktemp("validate")
    tmdl.build(star.build_star(tables), out)
    return out / f"{tmdl.PROJECT}.SemanticModel" / "definition"


# --- the generated project ---------------------------------------------------------------


def test_the_generated_project_is_structurally_valid(model_dir) -> None:
    errors = validate.validate_project(model_dir)
    assert not errors, "\n" + "\n".join(errors)


def test_the_committed_project_is_structurally_valid() -> None:
    """The one in the repository, not only the one a test just built."""
    definition = POWERBI_DIR / f"{tmdl.PROJECT}.SemanticModel" / "definition"
    if not definition.exists():
        pytest.skip("run `python -m bellwether.build` first")
    errors = validate.validate_project(definition)
    assert not errors, "\n" + "\n".join(errors)


# --- the defects it exists to catch, each one shipped at least once -----------------------


def test_a_table_property_after_a_column_is_rejected() -> None:
    """The exact file Power BI refused, reduced to four lines."""
    broken = "table dim_date\n\n\tcolumn 'Date'\n\t\tdataType: dateTime\n\n\tdataCategory: Time\n"
    errors = validate.validate_text(broken, "dim_date.tmdl")
    assert any("dataCategory" in e and "after a child object" in e for e in errors), errors


def test_the_correct_ordering_passes() -> None:
    good = "table dim_date\n\tdataCategory: Time\n\n\tcolumn 'Date'\n\t\tdataType: dateTime\n"
    assert not validate.validate_text(good, "dim_date.tmdl")


def test_a_table_with_no_columns_is_rejected() -> None:
    """The Measures table shipped like this: a partition, no column, parses fine, fails on load."""
    broken = "table Measures\n\n\tmeasure 'X' = 1\n\n\tpartition Measures = m\n\t\tmode: import\n"
    errors = validate.validate_table(broken, "Measures.tmdl")
    assert any("at least one column" in e for e in errors), errors


def test_spaces_instead_of_tabs_are_rejected() -> None:
    broken = "table X\n    dataCategory: Time\n"
    errors = validate.validate_text(broken, "X.tmdl")
    assert any("tabs only" in e for e in errors), errors


def test_an_indentation_jump_is_rejected() -> None:
    broken = "table X\n\t\t\tdataCategory: Time\n"
    errors = validate.validate_text(broken, "X.tmdl")
    assert any("indentation jumps" in e for e in errors), errors


def test_an_unknown_property_is_rejected() -> None:
    """A typo is otherwise accepted by the file and rejected by Desktop."""
    broken = "table X\n\tdataCatagory: Time\n"
    errors = validate.validate_text(broken, "X.tmdl")
    assert any("dataCatagory" in e for e in errors), errors


def test_a_child_in_the_wrong_parent_is_rejected() -> None:
    broken = "table X\n\n\tcolumn 'A'\n\t\tdataType: string\n\t\tcolumn 'B'\n"
    errors = validate.validate_text(broken, "X.tmdl")
    assert any("not a child of column" in e for e in errors), errors


def test_expression_valued_properties_are_not_mistaken_for_objects() -> None:
    """``source = let ... in ...`` is a property, not a child object.

    The validator's own first run reported this as an error on every table, which is a reminder
    that a checker with a wrong grammar is worse than no checker: it buries the one real finding
    in ten false ones.
    """
    good = (
        "table X\n\n\tcolumn 'A'\n\t\tdataType: string\n\n"
        "\tpartition X = m\n\t\tmode: import\n\t\tsource = let Source = 1 in Source\n"
    )
    assert not validate.validate_text(good, "X.tmdl")


def test_annotations_are_allowed_anywhere() -> None:
    good = "model Model\n\tculture: en-GB\n\n\tannotation __PBI_TimeIntelligenceEnabled = 0\n"
    assert not validate.validate_text(good, "model.tmdl")


# --- the properties the date table needs ---------------------------------------------------


def test_the_date_table_is_marked_and_keyed(model_dir) -> None:
    text = (model_dir / "tables" / "dim_date.tmdl").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[1] == "\tdataCategory: Time", lines[:3]
    assert "\t\tisKey" in text, "the date column identifies the table's date key"
    assert not validate.validate_table(text, "dim_date.tmdl")


def test_surrogate_keys_are_hidden(model_dir) -> None:
    """A report author should never see machinery in the field list."""
    text = (model_dir / "tables" / "dim_date.tmdl").read_text(encoding="utf-8")
    block = text.split("column 'Date key'")[1].split("column ")[0]
    assert "isHidden" in block


def test_no_boolean_or_key_column_is_summarised(model_dir) -> None:
    """ "Sum of Is promotional" is a number with no meaning that will end up on a slide."""
    for path in (model_dir / "tables").glob("*.tmdl"):
        text = path.read_text(encoding="utf-8")
        for block in text.split("\tcolumn ")[1:]:
            head = block.split("\tcolumn ")[0]
            if "dataType: boolean" in head or "dataType: string" in head:
                assert "summarizeBy: none" in head, f"{path.name}: {head.splitlines()[0]}"
