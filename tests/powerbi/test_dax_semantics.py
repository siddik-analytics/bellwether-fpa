"""Evaluate the emitted DAX against the star — criterion 5.32.

Phase 5's spec said the CI guarantee proves the measures were *generated*, not that they
evaluate. This narrows that gap without claiming to close it.

The two DAX shapes the generator emits are small enough to evaluate directly:

    CALCULATE(SUM(fact_metric[Value]), dim_metric[Metric] = "Gross Revenue")
    [Gross Revenue] - [Contra Revenue]

So these tests read the **emitted measure text** out of the measures table, evaluate it against the
same star Power BI will load, and assert it reproduces `statements.metric_series`. That catches a
generator that wrote the wrong metric name into a filter, mangled an expression, or pointed a
measure at the wrong column — none of which the "is it generated?" tests can see, because a
generator is perfectly capable of generating the wrong thing consistently.

**What this is not.** It is not Power BI's engine. It does not model filter context, relationship
propagation, blank handling or evaluation order, and a measure that is correct here can still be
wrong in Desktop for any of those reasons. Criterion 5.15 remains the real check and remains
manual. This is the difference between "the text was generated" and "the text means what the
semantic layer means", which is worth having and is not the same as "the report is right".
"""

from __future__ import annotations

import re

import pandas as pd
import pytest

from bellwether.data import generate
from bellwether.powerbi import tmdl
from bellwether.transform import expressions, semantic, star, statements

MEASURE = re.compile(r"^\tmeasure '([^']+)' = (.+)$", re.M)
BASE_SHAPE = re.compile(
    r"^CALCULATE\(SUM\((\w+)\[(\w+)\]\),\s*(\w+)\[(\w+)\]\s*=\s*\"([^\"]+)\"\)$"
)

KEYS = ["month", "version_name", "scenario_name"]


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    tables = generate.generate()
    schema = star.build_star(tables)
    out = tmp_path_factory.mktemp("dax")
    tmdl.build(schema, out)
    path = (
        out
        / f"{tmdl.PROJECT}.SemanticModel"
        / "definition"
        / "tables"
        / f"{tmdl.MEASURE_TABLE}.tmdl"
    )
    return {
        "measures": dict(MEASURE.findall(path.read_text(encoding="utf-8"))),
        "star": schema,
        "tables": tables,
    }


def _evaluate(measures: dict[str, str], fact: pd.DataFrame) -> dict[str, pd.Series]:
    """Evaluate every emitted measure against the fact table, at month x version x scenario.

    Base measures are resolved by reading the filter out of the DAX rather than by consulting
    the semantic layer — the point is to check what the file says, not what the file was
    supposed to say.
    """
    grid = fact.groupby(KEYS, as_index=False).size()[KEYS]
    values: dict[str, pd.Series] = {}

    for name, dax in measures.items():
        shape = BASE_SHAPE.match(dax)
        if not shape:
            continue
        _, value_column, _, filter_column, filter_value = shape.groups()
        physical_value = next(
            k for k, v in tmdl.COLUMN_NAMES.items() if v == value_column and k == "value"
        )
        subset = fact[fact["metric_name"] == filter_value]
        aggregated = subset.groupby(KEYS, as_index=False)[physical_value].sum()
        merged = grid.merge(aggregated, on=KEYS, how="left").fillna({physical_value: 0.0})
        values[name] = merged[physical_value]
        assert filter_column == "Metric", filter_column

    # Derived measures, in dependency order, evaluated from the emitted text.
    remaining = {n: d for n, d in measures.items() if n not in values and n != "Selection Status"}
    for _ in range(len(remaining) + 1):
        for name, dax in list(remaining.items()):
            references = expressions.dependencies(dax)
            if not references or any(r not in values for r in references):
                continue
            values[name] = expressions.evaluate(dax, values)
            remaining.pop(name)
    assert not remaining, f"could not evaluate {sorted(remaining)}"
    return {"grid": grid, **values}


def test_the_emitted_dax_reproduces_the_semantic_layer(project) -> None:
    """Every measure, every month, version and scenario — to the cent."""
    evaluated = _evaluate(project["measures"], project["star"]["fact_metric"])
    grid = evaluated.pop("grid")

    expected = statements.metric_series(
        project["tables"]["fact_gl"], project["tables"]["dim_gl_account"]
    )
    expected["month"] = pd.to_datetime(expected["month"])
    grid = grid.copy()
    grid["month"] = pd.to_datetime(grid["month"])

    worst: dict[str, float] = {}
    for name in semantic.ALL_METRICS:
        actual = grid.assign(dax=evaluated[name].to_numpy())
        merged = actual.merge(expected[[*KEYS, name]], on=KEYS, how="inner")
        assert len(merged) == len(grid), name
        worst[name] = float((merged["dax"] - merged[name]).abs().max())

    failures = {k: v for k, v in worst.items() if v > 0.01}
    assert not failures, failures


def test_a_base_measure_filters_on_its_own_name(project) -> None:
    """A generator that wrote the wrong name into a filter would still 'be generated'."""
    for name, dax in project["measures"].items():
        shape = BASE_SHAPE.match(dax)
        if not shape:
            continue
        assert shape.group(5) == name, f"{name} filters on {shape.group(5)}"


def test_every_measure_matches_one_of_the_two_known_shapes(project) -> None:
    """The translation surface, asserted rather than assumed.

    The verification strategy rests on the emitted DAX being small enough to read in one
    sitting. A third shape appearing is not necessarily wrong, but it is a change to that
    argument and should not pass silently.
    """
    unknown = []
    for name, dax in project["measures"].items():
        if name == "Selection Status":
            continue
        if BASE_SHAPE.match(dax):
            continue
        try:
            expressions.to_dax(dax)
        except expressions.DerivationError:
            unknown.append(f"{name}: {dax}")
    assert not unknown, unknown


def test_the_evaluator_would_notice_a_wrong_filter(project) -> None:
    """The negative control. A checker nobody has watched fail proves nothing."""
    tampered = dict(project["measures"])
    tampered["Gross Revenue"] = (
        'CALCULATE(SUM(fact_metric[Value]), dim_metric[Metric] = "Cost of Sales")'
    )
    evaluated = _evaluate(tampered, project["star"]["fact_metric"])
    honest = _evaluate(project["measures"], project["star"]["fact_metric"])
    assert not evaluated["Gross Revenue"].equals(honest["Gross Revenue"])
    assert not evaluated["Net Revenue"].equals(honest["Net Revenue"]), (
        "a wrong base measure must propagate into everything derived from it"
    )
